"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
import {
    Box, Container, Grid, Card, CardContent, Typography, CircularProgress,
    Paper, Chip, Divider, IconButton, LinearProgress, Alert, Tabs, Tab,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    TableSortLabel, Tooltip, ToggleButton, ToggleButtonGroup
} from "@mui/material";
import { ThemeProvider } from "@mui/material/styles";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import AccountBalanceIcon from "@mui/icons-material/AccountBalance";
import BarChartIcon from "@mui/icons-material/BarChart";
import PersonIcon from "@mui/icons-material/Person";
import CategoryIcon from "@mui/icons-material/Category";
import BusinessCenterIcon from "@mui/icons-material/BusinessCenter";
import { brandingDarkTheme, brandingLightTheme } from "../Themes/muiTheme";
import DrawerComponent from "../Reusable Components/Drawers/SideMenyDrawer";
import Link from "next/link";
import {
    Chart as ChartJS, CategoryScale, LinearScale, BarElement,
    Title, Tooltip as ChartTooltip, Legend
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, ChartTooltip, Legend);

const DB_NAME = process.env.NEXT_PUBLIC_DB_NAME || 'Investments';

// ── Palette ──────────────────────────────────────────────────────────────────
const positiveColor = (irr: number | null) => {
    if (irr === null || irr === undefined) return "#607D8B";
    if (irr > 0.15) return "#00C853";
    if (irr > 0.08) return "#4CAF50";
    if (irr > 0) return "#FFB700";
    return "#F44336";
};

// ── Types ────────────────────────────────────────────────────────────────────
interface AssetIRR {
    investment_name: string;
    institution: string;
    type: string;
    currency: string;
    irr: number | null;
    irr_pct: number | null;
}

interface GroupIRR {
    sector?: string;
    institution?: string;
    irr: number | null;
    irr_pct: number | null;
    investment_count: number;
}

interface IRRData {
    per_asset: AssetIRR[];
    by_sector: GroupIRR[];
    by_institution: GroupIRR[];
    whole_portfolio: { irr: number | null; irr_pct: number | null };
    portfolio_ex_ra: { irr: number | null; irr_pct: number | null; excluded_count: number };
    base_currency: string;
    generated_at: string;
    ra_types_excluded: string[];
    error?: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────
const fmtIRR = (v: number | null) =>
    v === null || v === undefined ? "N/A" : `${(v * 100).toFixed(2)}%`;

const fmtIRRPct = (v: number | null) =>
    v === null || v === undefined ? "N/A" : `${v.toFixed(2)}%`;

const IrrChip = ({ irr }: { irr: number | null }) => {
    const color = positiveColor(irr);
    const label = fmtIRR(irr);
    return (
        <Chip
            icon={irr !== null && irr >= 0 ? <TrendingUpIcon style={{ fontSize: 16, color }} /> : <TrendingDownIcon style={{ fontSize: 16, color }} />}
            label={label}
            size="small"
            sx={{
                backgroundColor: color + "22",
                color,
                fontWeight: 700,
                borderColor: color + "44",
                border: "1px solid"
            }}
        />
    );
};

// ── Main Component ────────────────────────────────────────────────────────────
export default function IRRAnalysis() {
    const [data, setData] = useState<IRRData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [darkMode, setDarkMode] = useState(false);
    const [tab, setTab] = useState(0);
    const [sortField, setSortField] = useState<"irr_pct" | "investment_name">("irr_pct");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

    const menuItems = [
        { heading: "Navigation", items: ["Dashboard", "Net Worth", "IRR Analysis", "Metrics", "Predictions", "Edit Data"], urls: ["/Investments", "/NetWorth", "/IRRAnalysis", "/ViewInvestmentMetrics", "/ViewInvestmentPredictions", "/EditInvestmentData"] }
    ];

    useEffect(() => {
        async function fetchData() {
            try {
                setLoading(true);
                const res = await axios.get(`/api/irr/${DB_NAME}?base_currency=ZAR`);
                setData(res.data);
                if (res.data.error) setError(res.data.error);
            } catch (err: any) {
                setError(err.message || "Failed to load IRR data");
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, []);

    const theme = darkMode ? brandingDarkTheme : brandingLightTheme;
    const bg = darkMode ? "#0d1117" : "#f0f2f5";
    const cardBg = darkMode ? "#161b22" : "#ffffff";
    const textPrimary = darkMode ? "#e6edf3" : "#0d1117";
    const textSecondary = darkMode ? "#8b949e" : "#57606a";
    const borderColor = darkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)";

    // ── Sorted assets ─────────────────────────────────────────────────────────
    const sortedAssets = data ? [...data.per_asset].sort((a, b) => {
        const av = sortField === "irr_pct" ? (a.irr_pct ?? -999) : a.investment_name.localeCompare(b.investment_name);
        const bv = sortField === "irr_pct" ? (b.irr_pct ?? -999) : b.investment_name.localeCompare(a.investment_name);
        if (sortField === "investment_name") return sortDir === "asc" ? (a.investment_name.localeCompare(b.investment_name)) : (b.investment_name.localeCompare(a.investment_name));
        return sortDir === "desc" ? ((b.irr_pct ?? -999) - (a.irr_pct ?? -999)) : ((a.irr_pct ?? -999) - (b.irr_pct ?? -999));
    }) : [];

    // ── Bar chart for sectors ─────────────────────────────────────────────────
    const makeBarData = (items: GroupIRR[], labelKey: "sector" | "institution") => {
        const sorted = [...items].sort((a, b) => (b.irr_pct ?? -999) - (a.irr_pct ?? -999));
        return {
            labels: sorted.map(it => {
                const name = it[labelKey] || "?";
                return name.length > 22 ? name.slice(0, 20) + "…" : name;
            }),
            datasets: [{
                label: "IRR (%)",
                data: sorted.map(it => it.irr_pct ?? 0),
                backgroundColor: sorted.map(it => positiveColor(it.irr) + "CC"),
                borderColor: sorted.map(it => positiveColor(it.irr)),
                borderWidth: 1,
                borderRadius: 6,
            }]
        };
    };

    const barOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (ctx: any) => ` IRR: ${ctx.raw.toFixed(2)}%` } }
        },
        scales: {
            y: { ticks: { callback: (v: any) => `${v}%`, color: darkMode ? "#aaa" : "#555" }, grid: { color: darkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)" } },
            x: { ticks: { color: darkMode ? "#aaa" : "#555" } }
        }
    };

    const IRRGauge = ({ irr, label, subtitle }: { irr: number | null; label: string; subtitle?: string }) => {
        const color = positiveColor(irr);
        const pct = irr !== null ? Math.min(Math.max(irr * 100, 0), 40) : 0;
        return (
            <Card elevation={0} sx={{
                backgroundColor: cardBg, borderRadius: 3, border: `1px solid ${borderColor}`,
                transition: "box-shadow 0.2s", "&:hover": { boxShadow: `0 4px 24px ${color}22` }
            }}>
                <CardContent sx={{ p: 3, textAlign: "center" }}>
                    <Typography variant="overline" sx={{ color: textSecondary, fontSize: 10, letterSpacing: 2 }}>
                        {label}
                    </Typography>
                    <Box sx={{ my: 2, position: "relative" }}>
                        <Box sx={{
                            width: 120, height: 120, borderRadius: "50%", mx: "auto",
                            background: `conic-gradient(${color} ${pct * 9}deg, ${darkMode ? "#2a2a3e" : "#e8e8e8"} 0deg)`,
                            display: "flex", alignItems: "center", justifyContent: "center",
                            boxShadow: `0 0 30px ${color}33`
                        }}>
                            <Box sx={{
                                width: 90, height: 90, borderRadius: "50%",
                                backgroundColor: cardBg,
                                display: "flex", alignItems: "center", justifyContent: "center"
                            }}>
                                <Typography variant="h5" sx={{ color, fontWeight: 800 }}>
                                    {irr !== null ? `${(irr * 100).toFixed(1)}%` : "N/A"}
                                </Typography>
                            </Box>
                        </Box>
                    </Box>
                    <Typography variant="body2" sx={{ color: textSecondary, fontSize: 12 }}>
                        {subtitle}
                    </Typography>
                </CardContent>
            </Card>
        );
    };

    return (
        <ThemeProvider theme={theme}>
            <Box sx={{ minHeight: "100vh", backgroundColor: bg, transition: "background-color 0.3s" }}>
                {/* Top bar */}
                <Box sx={{ display: "flex", alignItems: "center", p: 1, gap: 1, borderBottom: `1px solid ${borderColor}` }}>
                    <DrawerComponent menuItems={menuItems} />
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, ml: 1 }}>
                        <BarChartIcon sx={{ color: "#007FFF", fontSize: 28 }} />
                        <Typography variant="h6" sx={{ fontWeight: 700, color: textPrimary, letterSpacing: "-0.5px" }}>
                            IRR Analysis
                        </Typography>
                    </Box>
                    <Box sx={{ flex: 1 }} />
                    <Chip label="ZAR" size="small" sx={{ mr: 1, color: textSecondary }} />
                    <IconButton onClick={() => setDarkMode(d => !d)} sx={{ color: textSecondary }}>
                        {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
                    </IconButton>
                </Box>

                {loading && <LinearProgress sx={{ height: 3 }} />}

                <Container maxWidth="xl" sx={{ py: 4 }}>
                    {error && <Alert severity="warning" sx={{ mb: 3 }}>IRR data may be incomplete: {error}</Alert>}

                    {loading && !data && (
                        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 500, flexDirection: "column", gap: 3 }}>
                            <CircularProgress size={60} thickness={3} />
                            <Typography color="textSecondary">
                                Calculating IRR from transaction history…<br />
                                <Typography component="span" variant="caption" color="textSecondary">
                                    This may take a moment — XIRR is computed for every investment.
                                </Typography>
                            </Typography>
                        </Box>
                    )}

                    {data && (
                        <Grid container spacing={3}>

                            {/* ── Portfolio-level gauges ── */}
                            <Grid size={{ xs: 12 }}>
                                <Typography variant="h6" sx={{ fontWeight: 700, color: textPrimary, mb: 2 }}>
                                    Portfolio-Level IRR
                                </Typography>
                            </Grid>

                            <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                                <IRRGauge
                                    irr={data.whole_portfolio.irr}
                                    label="Whole Portfolio"
                                    subtitle="All investments combined"
                                />
                            </Grid>
                            <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                                <IRRGauge
                                    irr={data.portfolio_ex_ra.irr}
                                    label="Portfolio excl. RA"
                                    subtitle={`Excluding ${data.portfolio_ex_ra.excluded_count} RA investment(s)`}
                                />
                            </Grid>
                            <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                                <IRRGauge
                                    irr={data.by_sector.length ? (data.by_sector.reduce((a, b) => (a.irr_pct ?? 0) > (b.irr_pct ?? 0) ? a : b)).irr : null}
                                    label="Best Sector IRR"
                                    subtitle={data.by_sector.length ? (data.by_sector.reduce((a, b) => (a.irr_pct ?? 0) > (b.irr_pct ?? 0) ? a : b)).sector : "N/A"}
                                />
                            </Grid>
                            <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                                <IRRGauge
                                    irr={data.by_institution.length ? (data.by_institution.reduce((a, b) => (a.irr_pct ?? 0) > (b.irr_pct ?? 0) ? a : b)).irr : null}
                                    label="Best Institution IRR"
                                    subtitle={data.by_institution.length ? (data.by_institution.reduce((a, b) => (a.irr_pct ?? 0) > (b.irr_pct ?? 0) ? a : b)).institution : "N/A"}
                                />
                            </Grid>

                            {data.ra_types_excluded.length > 0 && (
                                <Grid size={{ xs: 12 }}>
                                    <Alert severity="info" sx={{ borderRadius: 2 }}>
                                        Retirement Annuity types excluded from "Portfolio excl. RA": {data.ra_types_excluded.join(", ")}
                                    </Alert>
                                </Grid>
                            )}

                            {/* ── Tabbed breakdown ── */}
                            <Grid size={{ xs: 12 }}>
                                <Card elevation={0} sx={{ backgroundColor: cardBg, borderRadius: 3, border: `1px solid ${borderColor}` }}>
                                    <Box sx={{ borderBottom: `1px solid ${borderColor}` }}>
                                        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ px: 2 }}>
                                            <Tab label="By Sector / Type" icon={<CategoryIcon />} iconPosition="start" sx={{ textTransform: "none", gap: 0.5 }} />
                                            <Tab label="By Institution" icon={<BusinessCenterIcon />} iconPosition="start" sx={{ textTransform: "none", gap: 0.5 }} />
                                            <Tab label="Per Asset" icon={<PersonIcon />} iconPosition="start" sx={{ textTransform: "none", gap: 0.5 }} />
                                        </Tabs>
                                    </Box>

                                    <CardContent sx={{ p: 3 }}>
                                        {/* ── By Sector ── */}
                                        {tab === 0 && (
                                            <>
                                                {data.by_sector.length > 0 ? (
                                                    <>
                                                        <Box sx={{ height: 300, mb: 4 }}>
                                                            <Bar data={makeBarData(data.by_sector, "sector")} options={barOptions as any} />
                                                        </Box>
                                                        <TableContainer>
                                                            <Table size="small">
                                                                <TableHead>
                                                                    <TableRow>
                                                                        <TableCell sx={{ color: textSecondary, fontWeight: 600 }}>Sector / Type</TableCell>
                                                                        <TableCell align="center" sx={{ color: textSecondary, fontWeight: 600 }}># Investments</TableCell>
                                                                        <TableCell align="center" sx={{ color: textSecondary, fontWeight: 600 }}>IRR</TableCell>
                                                                        <TableCell sx={{ color: textSecondary, fontWeight: 600 }}>Performance</TableCell>
                                                                    </TableRow>
                                                                </TableHead>
                                                                <TableBody>
                                                                    {[...data.by_sector].sort((a, b) => (b.irr_pct ?? -999) - (a.irr_pct ?? -999)).map((row, i) => (
                                                                        <TableRow key={i} sx={{ "&:hover": { backgroundColor: darkMode ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)" } }}>
                                                                            <TableCell sx={{ color: textPrimary, fontWeight: 600 }}>{row.sector}</TableCell>
                                                                            <TableCell align="center" sx={{ color: textSecondary }}>{row.investment_count}</TableCell>
                                                                            <TableCell align="center"><IrrChip irr={row.irr} /></TableCell>
                                                                            <TableCell>
                                                                                <LinearProgress variant="determinate"
                                                                                    value={Math.min(Math.max((row.irr_pct ?? 0), 0), 40) / 40 * 100}
                                                                                    sx={{
                                                                                        height: 6, borderRadius: 3, width: 120,
                                                                                        backgroundColor: darkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
                                                                                        "& .MuiLinearProgress-bar": { backgroundColor: positiveColor(row.irr), borderRadius: 3 }
                                                                                    }}
                                                                                />
                                                                            </TableCell>
                                                                        </TableRow>
                                                                    ))}
                                                                </TableBody>
                                                            </Table>
                                                        </TableContainer>
                                                    </>
                                                ) : <Typography color="textSecondary">No sector data available.</Typography>}
                                            </>
                                        )}

                                        {/* ── By Institution ── */}
                                        {tab === 1 && (
                                            <>
                                                {data.by_institution.length > 0 ? (
                                                    <>
                                                        <Box sx={{ height: 300, mb: 4 }}>
                                                            <Bar data={makeBarData(data.by_institution, "institution")} options={barOptions as any} />
                                                        </Box>
                                                        <TableContainer>
                                                            <Table size="small">
                                                                <TableHead>
                                                                    <TableRow>
                                                                        <TableCell sx={{ color: textSecondary, fontWeight: 600 }}>Institution</TableCell>
                                                                        <TableCell align="center" sx={{ color: textSecondary, fontWeight: 600 }}># Investments</TableCell>
                                                                        <TableCell align="center" sx={{ color: textSecondary, fontWeight: 600 }}>IRR</TableCell>
                                                                        <TableCell sx={{ color: textSecondary, fontWeight: 600 }}>Performance</TableCell>
                                                                    </TableRow>
                                                                </TableHead>
                                                                <TableBody>
                                                                    {[...data.by_institution].sort((a, b) => (b.irr_pct ?? -999) - (a.irr_pct ?? -999)).map((row, i) => (
                                                                        <TableRow key={i} sx={{ "&:hover": { backgroundColor: darkMode ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)" } }}>
                                                                            <TableCell sx={{ color: textPrimary, fontWeight: 600 }}>{row.institution}</TableCell>
                                                                            <TableCell align="center" sx={{ color: textSecondary }}>{row.investment_count}</TableCell>
                                                                            <TableCell align="center"><IrrChip irr={row.irr} /></TableCell>
                                                                            <TableCell>
                                                                                <LinearProgress variant="determinate"
                                                                                    value={Math.min(Math.max((row.irr_pct ?? 0), 0), 40) / 40 * 100}
                                                                                    sx={{
                                                                                        height: 6, borderRadius: 3, width: 120,
                                                                                        backgroundColor: darkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
                                                                                        "& .MuiLinearProgress-bar": { backgroundColor: positiveColor(row.irr), borderRadius: 3 }
                                                                                    }}
                                                                                />
                                                                            </TableCell>
                                                                        </TableRow>
                                                                    ))}
                                                                </TableBody>
                                                            </Table>
                                                        </TableContainer>
                                                    </>
                                                ) : <Typography color="textSecondary">No institution data available.</Typography>}
                                            </>
                                        )}

                                        {/* ── Per Asset ── */}
                                        {tab === 2 && (
                                            <TableContainer>
                                                <Table size="small">
                                                    <TableHead>
                                                        <TableRow>
                                                            <TableCell sx={{ color: textSecondary, fontWeight: 600 }}>
                                                                <TableSortLabel
                                                                    active={sortField === "investment_name"}
                                                                    direction={sortField === "investment_name" ? sortDir : "asc"}
                                                                    onClick={() => { setSortField("investment_name"); setSortDir(d => d === "asc" ? "desc" : "asc"); }}
                                                                >Investment</TableSortLabel>
                                                            </TableCell>
                                                            <TableCell sx={{ color: textSecondary, fontWeight: 600 }}>Type</TableCell>
                                                            <TableCell sx={{ color: textSecondary, fontWeight: 600 }}>Institution</TableCell>
                                                            <TableCell sx={{ color: textSecondary, fontWeight: 600 }}>Currency</TableCell>
                                                            <TableCell align="center" sx={{ color: textSecondary, fontWeight: 600 }}>
                                                                <TableSortLabel
                                                                    active={sortField === "irr_pct"}
                                                                    direction={sortField === "irr_pct" ? sortDir : "desc"}
                                                                    onClick={() => { setSortField("irr_pct"); setSortDir(d => d === "asc" ? "desc" : "asc"); }}
                                                                >IRR</TableSortLabel>
                                                            </TableCell>
                                                        </TableRow>
                                                    </TableHead>
                                                    <TableBody>
                                                        {sortedAssets.map((row, i) => (
                                                            <TableRow key={i} sx={{ "&:hover": { backgroundColor: darkMode ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)" } }}>
                                                                <TableCell sx={{ color: textPrimary, fontWeight: 600, maxWidth: 220, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                                                    <Tooltip title={row.investment_name}><span>{row.investment_name}</span></Tooltip>
                                                                </TableCell>
                                                                <TableCell><Chip label={row.type} size="small" sx={{ fontSize: 11 }} /></TableCell>
                                                                <TableCell sx={{ color: textSecondary, fontSize: 12 }}>{row.institution}</TableCell>
                                                                <TableCell><Chip label={row.currency} size="small" variant="outlined" sx={{ fontSize: 11 }} /></TableCell>
                                                                <TableCell align="center"><IrrChip irr={row.irr} /></TableCell>
                                                            </TableRow>
                                                        ))}
                                                    </TableBody>
                                                </Table>
                                            </TableContainer>
                                        )}
                                    </CardContent>
                                </Card>
                            </Grid>

                            {/* ── Back link ── */}
                            <Grid size={{ xs: 12 }}>
                                <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
                                    <Link href="/NetWorth" style={{ textDecoration: "none" }}>
                                        <Chip label="← Net Worth" clickable color="primary" />
                                    </Link>
                                    <Link href="/Investments" style={{ textDecoration: "none" }}>
                                        <Chip label="Dashboard" clickable variant="outlined" />
                                    </Link>
                                    <Link href="/ViewInvestmentMetrics" style={{ textDecoration: "none" }}>
                                        <Chip label="Metrics →" clickable variant="outlined" />
                                    </Link>
                                </Box>
                            </Grid>

                        </Grid>
                    )}
                </Container>
            </Box>
        </ThemeProvider>
    );
}
