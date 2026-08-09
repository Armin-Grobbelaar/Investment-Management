"use client";

import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
    Box, Container, Grid, Card, CardContent, Typography, CircularProgress,
    Paper, Chip, Divider, IconButton, ToggleButton, ToggleButtonGroup, Tooltip,
    LinearProgress, Alert
} from "@mui/material";
import { ThemeProvider } from "@mui/material/styles";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import PieChartIcon from "@mui/icons-material/PieChart";
import BusinessIcon from "@mui/icons-material/Business";
import CurrencyExchangeIcon from "@mui/icons-material/CurrencyExchange";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import InsightsIcon from "@mui/icons-material/Insights";
import HistoryIcon from "@mui/icons-material/History";
import PaymentsIcon from "@mui/icons-material/Payments";
import MoneyOffIcon from "@mui/icons-material/MoneyOff";
import { brandingDarkTheme, brandingLightTheme } from "../Themes/muiTheme";
import DrawerComponent from "../Reusable Components/Drawers/SideMenyDrawer";
import Link from "next/link";
import {
    Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement,
    Title, Tooltip as ChartTooltip, Legend, Filler, ArcElement, BarElement
} from "chart.js";
import { Line, Doughnut, Bar } from "react-chartjs-2";

ChartJS.register(
    CategoryScale, LinearScale, PointElement, LineElement,
    Title, ChartTooltip, Legend, Filler, ArcElement, BarElement
);

const DB_NAME = process.env.NEXT_PUBLIC_DB_NAME || 'Investments';

// ── Colour palette ──────────────────────────────────────────────────────────
const PALETTE = [
    "#007FFF","#00C853","#FF6B35","#FFB700","#9C27B0",
    "#00BCD4","#FF5722","#4CAF50","#FFC107","#E91E63",
    "#3F51B5","#009688","#795548","#607D8B","#F44336",
];

// ── Types ───────────────────────────────────────────────────────────────────
interface BreakdownItem {
    type?: string;
    institution?: string;
    currency?: string;
    value: number;
    pct: number;
    count: number;
}

interface TimeSeriesPoint { date: string; value: number; }

interface NetWorthData {
    total_net_worth: number;
    total_net_worth_formatted: string;
    by_type: BreakdownItem[];
    by_institution: BreakdownItem[];
    by_currency: BreakdownItem[];
    timeseries: TimeSeriesPoint[];
    investment_count: number;
    base_currency: string;
    timestamp: string;
    total_contributions: number | null;
    total_fees: number | null;
    portfolio_cagr: number | null;
    portfolio_irr: number | null;
}

// ── Formatting helpers ───────────────────────────────────────────────────────
const fmt = (n: number) => `R ${new Intl.NumberFormat("en-ZA", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n)}`;

const fmtShort = (n: number) => {
    if (n >= 1_000_000) return `R${(n / 1_000_000).toFixed(2)}M`;
    if (n >= 1_000)     return `R${(n / 1_000).toFixed(1)}K`;
    return `R${n.toFixed(0)}`;
};

// ── Main Component ───────────────────────────────────────────────────────────
export default function NetWorthTracker() {
    const [data, setData] = useState<NetWorthData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [darkMode, setDarkMode] = useState(false);
    const [timeRange, setTimeRange] = useState<"all" | "1y" | "3y" | "5y">("all");
    const [activeBreakdown, setActiveBreakdown] = useState<"type" | "institution" | "currency">("type");
    const chartRef = useRef<ChartJS<"line"> | null>(null);

    const menuItems = [
        { heading: "Navigation", items: ["Dashboard", "Net Worth", "IRR Analysis", "Property Analysis", "Metrics", "Predictions", "Edit Data"], urls: ["/Investments", "/NetWorth", "/IRRAnalysis", "/PropertyAnalysis", "/ViewInvestmentMetrics", "/ViewInvestmentPredictions", "/EditInvestmentData"] }
    ];

    useEffect(() => {
        async function fetchData() {
            try {
                setLoading(true);
                const res = await axios.get(`/api/net_worth/${DB_NAME}?base_currency=ZAR`);
                setData(res.data);
            } catch (err: any) {
                setError(err.message || "Failed to load net worth data");
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, []);

    // ── Filter timeseries by selected range ──────────────────────────────────
    const filteredTimeseries = (() => {
        if (!data?.timeseries?.length) return [];
        const sorted = [...data.timeseries].sort((a, b) => a.date.localeCompare(b.date));
        if (timeRange === "all") return sorted;
        const cutoff = new Date();
        const years = timeRange === "1y" ? 1 : timeRange === "3y" ? 3 : 5;
        cutoff.setFullYear(cutoff.getFullYear() - years);
        return sorted.filter(p => new Date(p.date) >= cutoff);
    })();

    // ── Determine net worth change ────────────────────────────────────────────
    const netWorthChange = (() => {
        if (filteredTimeseries.length < 2) return null;
        const first = filteredTimeseries[0].value;
        const last  = filteredTimeseries[filteredTimeseries.length - 1].value;
        return { abs: last - first, pct: first > 0 ? ((last - first) / first) * 100 : 0 };
    })();

    // ── Chart data ───────────────────────────────────────────────────────────
    const lineChartData = {
        labels: filteredTimeseries.map(p => p.date),
        datasets: [{
            label: "Portfolio Value",
            data: filteredTimeseries.map(p => p.value),
            borderColor: "#007FFF",
            backgroundColor: "rgba(0,127,255,0.12)",
            fill: true,
            tension: 0.3,
            pointRadius: filteredTimeseries.length > 200 ? 0 : 2,
            borderWidth: 2,
        }]
    };

    const lineChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: (ctx: any) => ` ${fmtShort(ctx.raw)}`
                }
            }
        },
        scales: {
            x: {
                ticks: { maxTicksLimit: 10, color: darkMode ? "#aaa" : "#555" },
                grid: { color: darkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)" }
            },
            y: {
                ticks: { callback: (v: any) => fmtShort(v), color: darkMode ? "#aaa" : "#555" },
                grid: { color: darkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)" }
            }
        }
    };

    const activeItems: BreakdownItem[] =
        activeBreakdown === "type"        ? (data?.by_type        ?? []) :
        activeBreakdown === "institution" ? (data?.by_institution ?? []) :
                                           (data?.by_currency     ?? []);

    const doughnutData = {
        labels: activeItems.map(it => it.type || it.institution || it.currency || "?"),
        datasets: [{
            data: activeItems.map(it => it.pct),
            backgroundColor: PALETTE.slice(0, activeItems.length),
            borderWidth: 2,
            borderColor: darkMode ? "#1a1a2e" : "#fff",
        }]
    };

    const doughnutOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position: "right" as const, labels: { color: darkMode ? "#eee" : "#333", padding: 14, boxWidth: 14 } },
            tooltip: { callbacks: { label: (ctx: any) => ` ${ctx.label}: ${ctx.raw.toFixed(1)}%` } }
        },
        cutout: "60%"
    };

    // ── Bar chart for breakdowns ─────────────────────────────────────────────
    const barData = {
        labels: activeItems.map(it => {
            const name = it.type || it.institution || it.currency || "?";
            return name.length > 20 ? name.slice(0, 18) + "…" : name;
        }),
        datasets: [{
            label: "Value (ZAR)",
            data: activeItems.map(it => it.value),
            backgroundColor: PALETTE.slice(0, activeItems.length).map(c => c + "CC"),
            borderColor: PALETTE.slice(0, activeItems.length),
            borderWidth: 1,
            borderRadius: 6,
        }]
    };

    const barOptions = {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y" as const,
        plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (ctx: any) => ` ${fmtShort(ctx.raw)}` } }
        },
        scales: {
            x: {
                ticks: { callback: (v: any) => fmtShort(v), color: darkMode ? "#aaa" : "#555" },
                grid: { color: darkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)" }
            },
            y: { ticks: { color: darkMode ? "#aaa" : "#555" } }
        }
    };

    const theme = darkMode ? brandingDarkTheme : brandingLightTheme;
    const bg = darkMode ? "#001E3C" : "#fff";
    const cardBg = darkMode ? "#0A1929" : "#ffffff";
    const textPrimary = darkMode ? "#ffffff" : "#1A2027";
    const textSecondary = darkMode ? "#B2BAC2" : "#6F7E8C";
    const borderColor = darkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)";

    // ── Render ───────────────────────────────────────────────────────────────
    return (
        <ThemeProvider theme={theme}>
            <Box sx={{ minHeight: "100vh", backgroundColor: bg, transition: "background-color 0.3s" }}>

                {/* Top bar */}
                <Box sx={{ display: "flex", alignItems: "center", p: 1, gap: 1, borderBottom: `1px solid ${borderColor}` }}>
                    <DrawerComponent menuItems={menuItems} />
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, ml: 1 }}>
                        <AccountBalanceWalletIcon sx={{ color: "#007FFF", fontSize: 28 }} />
                        <Typography variant="h6" sx={{ fontWeight: 700, color: textPrimary, letterSpacing: "-0.5px" }}>
                            Net Worth Tracker
                        </Typography>
                    </Box>
                    <Box sx={{ flex: 1 }} />
                    <IconButton onClick={() => setDarkMode(d => !d)} sx={{ color: textSecondary }}>
                        {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
                    </IconButton>
                </Box>

                {loading && <LinearProgress sx={{ height: 3 }} />}

                <Container maxWidth="xl" sx={{ py: 4 }}>

                    {error && (
                        <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
                    )}

                    {loading && !data && (
                        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 400, flexDirection: "column", gap: 3 }}>
                            <CircularProgress size={60} thickness={3} />
                            <Typography color="textSecondary">Loading portfolio data…</Typography>
                        </Box>
                    )}

                    {data && (
                        <Grid container spacing={3}>

                            {/* ── Hero metric card ── */}
                            <Grid size={{ xs: 12, lg: 4 }}>
                                <Card elevation={0} sx={{
                                    background: "linear-gradient(135deg, #007FFF 0%, #0054a8 100%)",
                                    borderRadius: 4, p: 1, height: "100%",
                                    boxShadow: "0 8px 32px rgba(0,127,255,0.3)"
                                }}>
                                    <CardContent sx={{ p: 3 }}>
                                        <Typography variant="overline" sx={{ color: "rgba(255,255,255,0.75)", letterSpacing: 2, fontSize: 11 }}>
                                            TOTAL NET WORTH
                                        </Typography>
                                        <Typography variant="h3" sx={{ color: "#fff", fontWeight: 800, mt: 1, letterSpacing: "-1px" }}>
                                            {data.total_net_worth_formatted || fmt(data.total_net_worth)}
                                        </Typography>
                                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 2 }}>
                                            <Chip
                                                icon={<TrendingUpIcon style={{ color: "#fff" }} />}
                                                label={`${data.investment_count} investments`}
                                                sx={{ backgroundColor: "rgba(255,255,255,0.18)", color: "#fff", fontWeight: 600 }}
                                                size="small"
                                            />
                                            <Chip
                                                label={data.base_currency}
                                                sx={{ backgroundColor: "rgba(255,255,255,0.12)", color: "#fff" }}
                                                size="small"
                                            />
                                        </Box>
                                        {netWorthChange && (
                                            <Box sx={{ mt: 3 }}>
                                                <Divider sx={{ borderColor: "rgba(255,255,255,0.2)", mb: 2 }} />
                                                <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.7)" }}>
                                                    Change ({timeRange === "all" ? "All time" : timeRange})
                                                </Typography>
                                                <Typography variant="h6" sx={{ color: netWorthChange.abs >= 0 ? "#69ff47" : "#ff6b6b", fontWeight: 700 }}>
                                                    {netWorthChange.abs >= 0 ? "+" : ""}{fmtShort(netWorthChange.abs)}
                                                    {"  "}({netWorthChange.pct >= 0 ? "+" : ""}{netWorthChange.pct.toFixed(1)}%)
                                                </Typography>
                                            </Box>
                                        )}
                                    </CardContent>
                                </Card>
                            </Grid>
                            
                            {/* ── Performance metric cards ── */}
                            {[
                                {
                                    label: "Portfolio CAGR",
                                    icon: <InsightsIcon sx={{ color: "#007FFF" }} />,
                                    value: data.portfolio_cagr !== null ? `${data.portfolio_cagr.toFixed(2)}%` : "–",
                                    sub: "Annualized Return",
                                    color: "#007FFF"
                                },
                                {
                                    label: "Portfolio IRR",
                                    icon: <HistoryIcon sx={{ color: "#00C853" }} />,
                                    value: data.portfolio_irr !== null ? `${data.portfolio_irr.toFixed(2)}%` : "–",
                                    sub: "Internal Rate of Return",
                                    color: "#00C853"
                                },
                                {
                                    label: "Total Contributions",
                                    icon: <PaymentsIcon sx={{ color: "#FFB700" }} />,
                                    value: data.total_contributions !== null ? fmtShort(data.total_contributions) : "–",
                                    sub: "Lifetime Invested",
                                    color: "#FFB700"
                                },
                                {
                                    label: "Total Fees Paid",
                                    icon: <MoneyOffIcon sx={{ color: "#FF5722" }} />,
                                    value: data.total_fees !== null ? fmtShort(data.total_fees) : "–",
                                    sub: "Investment Costs",
                                    color: "#FF5722"
                                }
                            ].map((stat, i) => (
                                <Grid key={i} size={{ xs: 12, sm: 6, lg: 3 }}>
                                    <Card elevation={0} sx={{
                                        backgroundColor: cardBg, borderRadius: 3,
                                        border: `1px solid ${borderColor}`, height: "100%",
                                        transition: "box-shadow 0.2s",
                                        "&:hover": { boxShadow: `0 4px 20px ${stat.color}15` }
                                    }}>
                                        <CardContent sx={{ p: 2.5 }}>
                                            <Box sx={{ display: "flex", alignItems: "center", gap: 1.2, mb: 1.5 }}>
                                                {stat.icon}
                                                <Typography variant="overline" sx={{ color: textSecondary, fontSize: 10, letterSpacing: 1.2 }}>
                                                    {stat.label}
                                                </Typography>
                                            </Box>
                                            <Typography variant="h5" sx={{ color: textPrimary, fontWeight: 700 }}>
                                                {stat.value}
                                            </Typography>
                                            <Typography variant="caption" sx={{ color: textSecondary }}>
                                                {stat.sub}
                                            </Typography>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            ))}

                            {/* ── Stat cards ── */}
                            {[
                                {
                                    label: "Largest Sector",
                                    icon: <PieChartIcon sx={{ color: "#00C853" }} />,
                                    value: data.by_type[0]?.type || "–",
                                    sub: `${(data.by_type[0]?.pct || 0).toFixed(1)}% of portfolio`,
                                    color: "#00C853"
                                },
                                {
                                    label: "Top Institution",
                                    icon: <BusinessIcon sx={{ color: "#FF6B35" }} />,
                                    value: data.by_institution[0]?.institution || "–",
                                    sub: `${fmtShort(data.by_institution[0]?.value || 0)} invested`,
                                    color: "#FF6B35"
                                },
                                {
                                    label: "Primary Currency",
                                    icon: <CurrencyExchangeIcon sx={{ color: "#FFB700" }} />,
                                    value: data.by_currency[0]?.currency || "–",
                                    sub: `${(data.by_currency[0]?.pct || 0).toFixed(1)}% of assets`,
                                    color: "#FFB700"
                                }
                            ].map((stat, i) => (
                                <Grid key={i} size={{ xs: 12, sm: 4, lg: 8 / 3 }}>
                                    <Card elevation={0} sx={{
                                        backgroundColor: cardBg, borderRadius: 3,
                                        border: `1px solid ${borderColor}`, height: "100%",
                                        transition: "box-shadow 0.2s",
                                        "&:hover": { boxShadow: `0 4px 24px ${stat.color}22` }
                                    }}>
                                        <CardContent sx={{ p: 3 }}>
                                            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
                                                {stat.icon}
                                                <Typography variant="overline" sx={{ color: textSecondary, fontSize: 10, letterSpacing: 1.5 }}>
                                                    {stat.label}
                                                </Typography>
                                            </Box>
                                            <Typography variant="h6" sx={{ color: textPrimary, fontWeight: 700, wordBreak: "break-word" }}>
                                                {stat.value}
                                            </Typography>
                                            <Typography variant="caption" sx={{ color: textSecondary }}>
                                                {stat.sub}
                                            </Typography>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            ))}

                            {/* ── Portfolio value over time chart ── */}
                            <Grid size={{ xs: 12 }}>
                                <Card elevation={0} sx={{
                                    backgroundColor: cardBg, borderRadius: 3,
                                    border: `1px solid ${borderColor}`
                                }}>
                                    <CardContent sx={{ p: 3 }}>
                                        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3, flexWrap: "wrap", gap: 2 }}>
                                            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                                                <ShowChartIcon sx={{ color: "#007FFF" }} />
                                                <Typography variant="h6" sx={{ fontWeight: 700, color: textPrimary }}>
                                                    Portfolio Value Over Time
                                                </Typography>
                                            </Box>
                                            <ToggleButtonGroup
                                                value={timeRange}
                                                exclusive
                                                onChange={(_, v) => v && setTimeRange(v)}
                                                size="small"
                                            >
                                                {(["1y", "3y", "5y", "all"] as const).map(r => (
                                                    <ToggleButton key={r} value={r} sx={{ textTransform: "none", fontWeight: 600, px: 2 }}>
                                                        {r.toUpperCase()}
                                                    </ToggleButton>
                                                ))}
                                            </ToggleButtonGroup>
                                        </Box>
                                        {filteredTimeseries.length > 1 ? (
                                            <Box sx={{ height: 350 }}>
                                                <Line data={lineChartData} options={lineChartOptions as any} />
                                            </Box>
                                        ) : (
                                            <Box sx={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                <Typography color="textSecondary">No time-series data available yet.</Typography>
                                            </Box>
                                        )}
                                    </CardContent>
                                </Card>
                            </Grid>

                            {/* ── Breakdown section ── */}
                            <Grid size={{ xs: 12 }}>
                                <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
                                    <Typography variant="h6" sx={{ fontWeight: 700, color: textPrimary }}>
                                        Portfolio Breakdown
                                    </Typography>
                                    <ToggleButtonGroup
                                        value={activeBreakdown}
                                        exclusive
                                        onChange={(_, v) => v && setActiveBreakdown(v)}
                                        size="small"
                                    >
                                        <ToggleButton value="type" sx={{ textTransform: "none", gap: 0.5 }}>
                                            <PieChartIcon fontSize="small" /> By Type
                                        </ToggleButton>
                                        <ToggleButton value="institution" sx={{ textTransform: "none", gap: 0.5 }}>
                                            <BusinessIcon fontSize="small" /> By Institution
                                        </ToggleButton>
                                        <ToggleButton value="currency" sx={{ textTransform: "none", gap: 0.5 }}>
                                            <CurrencyExchangeIcon fontSize="small" /> By Currency
                                        </ToggleButton>
                                    </ToggleButtonGroup>
                                </Box>
                            </Grid>

                            {/* Doughnut */}
                            <Grid size={{ xs: 12, md: 5 }}>
                                <Card elevation={0} sx={{
                                    backgroundColor: cardBg, borderRadius: 3,
                                    border: `1px solid ${borderColor}`, height: 380,
                                    display: "flex", alignItems: "center", justifyContent: "center"
                                }}>
                                    <CardContent sx={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                        {activeItems.length > 0 ? (
                                            <Box sx={{ width: "100%", height: 320 }}>
                                                <Doughnut data={doughnutData} options={doughnutOptions as any} />
                                            </Box>
                                        ) : (
                                            <Typography color="textSecondary">No data</Typography>
                                        )}
                                    </CardContent>
                                </Card>
                            </Grid>

                            {/* Horizontal bar */}
                            <Grid size={{ xs: 12, md: 7 }}>
                                <Card elevation={0} sx={{
                                    backgroundColor: cardBg, borderRadius: 3,
                                    border: `1px solid ${borderColor}`, height: 380
                                }}>
                                    <CardContent sx={{ height: "100%", p: 3 }}>
                                        <Typography variant="subtitle2" sx={{ color: textSecondary, mb: 2 }}>
                                            Value by {activeBreakdown === "type" ? "Sector" : activeBreakdown === "institution" ? "Institution" : "Currency"}
                                        </Typography>
                                        {activeItems.length > 0 ? (
                                            <Box sx={{ height: 290 }}>
                                                <Bar data={barData} options={barOptions as any} />
                                            </Box>
                                        ) : (
                                            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: 290 }}>
                                                <Typography color="textSecondary">No data</Typography>
                                            </Box>
                                        )}
                                    </CardContent>
                                </Card>
                            </Grid>

                            {/* ── Detailed breakdown table ── */}
                            <Grid size={{ xs: 12 }}>
                                <Card elevation={0} sx={{ backgroundColor: cardBg, borderRadius: 3, border: `1px solid ${borderColor}` }}>
                                    <CardContent sx={{ p: 3 }}>
                                        <Typography variant="h6" sx={{ fontWeight: 700, color: textPrimary, mb: 3 }}>
                                            Detailed Breakdown
                                        </Typography>
                                        {activeItems.map((item, idx) => {
                                            const name = item.type || item.institution || item.currency || "?";
                                            return (
                                                <Box key={idx} sx={{ mb: 2 }}>
                                                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                                                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                                            <Box sx={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: PALETTE[idx % PALETTE.length] }} />
                                                            <Typography variant="body2" sx={{ color: textPrimary, fontWeight: 600 }}>
                                                                {name}
                                                            </Typography>
                                                            <Typography variant="caption" sx={{ color: textSecondary }}>
                                                                ({item.count} {item.count === 1 ? "investment" : "investments"})
                                                            </Typography>
                                                        </Box>
                                                        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                                                            <Typography variant="body2" sx={{ color: textSecondary }}>
                                                                {item.pct.toFixed(1)}%
                                                            </Typography>
                                                            <Typography variant="body2" sx={{ color: textPrimary, fontWeight: 700, minWidth: 100, textAlign: "right" }}>
                                                                {fmtShort(item.value)}
                                                            </Typography>
                                                        </Box>
                                                    </Box>
                                                    <LinearProgress
                                                        variant="determinate"
                                                        value={Math.min(item.pct, 100)}
                                                        sx={{
                                                            height: 6, borderRadius: 3,
                                                            backgroundColor: darkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
                                                            "& .MuiLinearProgress-bar": {
                                                                backgroundColor: PALETTE[idx % PALETTE.length],
                                                                borderRadius: 3
                                                            }
                                                        }}
                                                    />
                                                </Box>
                                            );
                                        })}
                                    </CardContent>
                                </Card>
                            </Grid>

                            {/* ── IRR link card ── */}
                            <Grid size={{ xs: 12 }}>
                                <Card elevation={0} sx={{
                                    background: "linear-gradient(135deg, #001E3C 0%, #173A5E 50%, #0059B2 100%)",
                                    borderRadius: 3, p: 1
                                }}>
                                    <CardContent sx={{ p: 3, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 2 }}>
                                        <Box>
                                            <Typography variant="h6" sx={{ color: "#fff", fontWeight: 700 }}>
                                                📈 IRR Analysis
                                            </Typography>
                                            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.65)", mt: 0.5 }}>
                                                View Internal Rate of Return per asset, by sector, institution, and portfolio level
                                            </Typography>
                                        </Box>
                                        <Link href="/IRRAnalysis" style={{ textDecoration: "none" }}>
                                            <Box sx={{
                                                px: 3, py: 1.5, borderRadius: 2,
                                                background: "rgba(0,127,255,0.9)",
                                                color: "#fff", fontWeight: 700, fontSize: 14,
                                                cursor: "pointer", transition: "background 0.2s",
                                                "&:hover": { background: "#007FFF" }
                                            }}>
                                                View IRR Analysis →
                                            </Box>
                                        </Link>
                                    </CardContent>
                                </Card>
                            </Grid>

                        </Grid>
                    )}
                </Container>
            </Box>
        </ThemeProvider>
    );
}
