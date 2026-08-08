'use client';

import React, { useState, useEffect } from 'react';
import {
    Container, Paper, IconButton, Select, MenuItem, FormControl,
    InputLabel, Box, Typography, Chip, Card, CardContent,
    Tabs, Tab, CircularProgress, Divider, Alert, Tooltip as MuiTooltip,
    Table, TableContainer, TableHead, TableBody, TableRow, TableCell,
} from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import MoneyOffIcon from '@mui/icons-material/MoneyOff';
import SavingsIcon from '@mui/icons-material/Savings';
import BarChartIcon from '@mui/icons-material/BarChart';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import RefreshIcon from '@mui/icons-material/Refresh';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';
import KeyboardBackspaceIcon from '@mui/icons-material/KeyboardBackspace';
import { useRouter } from 'next/navigation';
import { Line, Bar } from 'react-chartjs-2';
import {
    Chart as ChartJS, CategoryScale, LinearScale, PointElement,
    LineElement, BarElement, Title, Tooltip as ChartTooltip,
    Legend, Filler
} from 'chart.js';
import axios from 'axios';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, ChartTooltip, Legend, Filler);

const DB_NAME = process.env.NEXT_PUBLIC_DB_NAME || 'Investments';

const CHART_COLORS: Record<string, string> = {
    blue: '#2196f3', green: '#4caf50', red: '#f44336', purple: '#9c27b0',
    orange: '#ff9800', teal: '#009688', pink: '#e91e63', indigo: '#3f51b5',
    amber: '#ffc107', cyan: '#00bcd4', grey: '#9e9e9e',
};

const METRIC_THEMES: Record<string, { bg: string; icon: React.ReactNode }> = {
    total_value: { bg: 'linear-gradient(135deg, #1565c0, #1976d2)', icon: <AccountBalanceWalletIcon sx={{ fontSize: 40 }} /> },
    total_return: { bg: 'linear-gradient(135deg, #2e7d32, #388e3c)', icon: <TrendingUpIcon sx={{ fontSize: 40 }} /> },
    cagr_irr: { bg: 'linear-gradient(135deg, #6a1b9a, #7b1fa2)', icon: <ShowChartIcon sx={{ fontSize: 40 }} /> },
    total_fees: { bg: 'linear-gradient(135deg, #c62828, #d32f2f)', icon: <MoneyOffIcon sx={{ fontSize: 40 }} /> },
};

const ComparisonView = ({ data, fmtCurrency, fmtPct }: { data: any; fmtCurrency: (v: number) => string; fmtPct: (v: number) => string }) => {
    if (!data || !data.groups || data.groups.length === 0) {
        return (
            <Paper elevation={1} sx={{ p: 4, borderRadius: 3 }}>
                <Typography variant="body1" color="text.secondary" align="center">
                    No assets are held in more than one account yet. When you hold the same fund or
                    ETF in multiple accounts, it appears here so you can compare its metrics.
                </Typography>
            </Paper>
        );
    }
    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {data.groups.map((group: any, gi: number) => (
                <Paper key={`${group.asset}-${gi}`} elevation={2} sx={{ borderRadius: 3, p: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5, flexWrap: 'wrap', gap: 1 }}>
                        <Box>
                            <Typography variant="h6" fontWeight="bold">{group.asset}</Typography>
                            <Typography variant="caption" color="text.secondary">
                                Same asset in {group.accounts.length} accounts · {group.source} · {group.currency}
                            </Typography>
                        </Box>
                        <Chip label={`Combined value: ${fmtCurrency(group.total_value)}`} color="primary" variant="outlined" />
                    </Box>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell sx={{ fontWeight: 'bold' }}>Account / Institution</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Units</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Price</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Value</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Contributions</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Net Growth</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Total Return</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>IRR</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>CAGR</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Period</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Share</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {group.accounts.map((acc: any) => (
                                    <TableRow key={acc.id} hover>
                                        <TableCell>
                                            <Typography variant="body2" fontWeight="medium">{acc.name}</Typography>
                                            <Typography variant="caption" color="text.secondary">{acc.institution}</Typography>
                                        </TableCell>
                                        <TableCell align="right">{acc.units}</TableCell>
                                        <TableCell align="right">{acc.current_price}</TableCell>
                                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>{fmtCurrency(acc.current_value)}</TableCell>
                                        <TableCell align="right">{fmtCurrency(acc.total_contributions)}</TableCell>
                                        <TableCell align="right" sx={{ color: (acc.net_growth ?? 0) >= 0 ? 'success.main' : 'error.main' }}>{fmtCurrency(acc.net_growth)}</TableCell>
                                        <TableCell align="right" sx={{ color: (acc.total_return_pct ?? 0) >= 0 ? 'success.main' : 'error.main' }}>{fmtPct(acc.total_return_pct)}</TableCell>
                                        <TableCell align="right" sx={{ color: (acc.irr_pct ?? 0) >= 0 ? 'success.main' : 'error.main' }}>{fmtPct(acc.irr_pct)}</TableCell>
                                        <TableCell align="right">{fmtPct(acc.cagr_pct)}</TableCell>
                                        <TableCell align="right">{acc.period_years ?? 'N/A'} yrs</TableCell>
                                        <TableCell align="right">{acc.share_pct}%</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Paper>
            ))}
        </Box>
    );
};

export default function EnhancedViewInvestmentMetrics() {
    const router = useRouter();
    const [darkMode, setDarkMode] = useState(true);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [dimensionData, setDimensionData] = useState<any>(null);
    const [dimensionType, setDimensionType] = useState<number>(0);
    const [dimensionValue, setDimensionValue] = useState<string>('All');
    const [metricsData, setMetricsData] = useState<any>(null);
    const [comparisonData, setComparisonData] = useState<any>(null);
    const [chartTab, setChartTab] = useState<number>(0);
    const [menuItems] = useState<any[]>([
        { heading: "Tools & Analysis", items: ["Dashboard", "Factsheets", "Property Analysis", "Monte Carlo Simulations"], urls: ["/Investments", "/Factsheets", "/PropertyAnalysis", "/ViewInvestmentPredictions"] }
    ]);

    const toggleDarkMode = () => setDarkMode(prev => !prev);
    const theme = darkMode ? brandingDarkTheme : brandingLightTheme;

    const DIMENSIONS = [
        { label: "Per Investment", id: "investment", arrayName: "investment_names" },
        { label: "By Product Type", id: "investment_type", arrayName: "investment_types" },
        { label: "By Institution", id: "institution", arrayName: "institutions" },
        { label: "By Account Type", id: "account_type", arrayName: "account_types" },
        { label: "By Currency", id: "currency", arrayName: "currencies" },
        { label: "Portfolio Total", id: "portfolio", arrayName: null },
        { label: "Across Accounts", id: "comparison", arrayName: null },
    ];

    const CHART_GROUPS = [
        { label: "Performance", id: 0 }, { label: "Risk & Volatility", id: 1 },
        { label: "Income & Costs", id: 2 }, { label: "Drawdown & Benchmarks", id: 3 },
    ];

    useEffect(() => {
        const fetchDimensions = async () => {
            try {
                const response = await axios.get('/api/investment_names');
                setDimensionData(response.data);
                setDimensionValue(response.data.investment_names?.[0] || 'All');
            } catch (err) {
                console.error('Failed to load dimensions', err);
                setError('Failed to load investment dimensions. Ensure the backend is running.');
            }
            setLoading(false);
        };
        fetchDimensions();
    }, []);

    useEffect(() => {
        if (!dimensionData && loading) return;
        const fetchMetrics = async () => {
            setLoading(true);
            setError(null);
            try {
                const currentDim = DIMENSIONS[dimensionType];
                if (currentDim.id === 'comparison') {
                    const response = await axios.get(`/api/investment_comparison/${DB_NAME}`);
                    setComparisonData(response.data);
                    setMetricsData(null);
                    setLoading(false);
                    return;
                }
                let filter = currentDim.id;
                if (filter !== 'portfolio') {
                    filter = filter === 'investment' ? dimensionValue : `${filter}:${dimensionValue}`;
                }
                const url = currentDim.id === 'investment'
                    ? `/api/investment_metrics_by_name/${DB_NAME}/${encodeURIComponent(filter)}`
                    : `/api/investment_metrics/${DB_NAME}?filter=${encodeURIComponent(filter)}`;
                const response = await axios.get(url);
                setMetricsData(response.data);
            } catch (err) {
                console.error('Failed to load metrics data', err);
                setMetricsData(null);
                setError('Failed to load metrics. Try a different selection or ensure metrics have been calculated.');
            }
            setLoading(false);
        };
        fetchMetrics();
    }, [dimensionType, dimensionValue, dimensionData]);

    const handleDimensionChange = (_: React.SyntheticEvent, newValue: number) => {
        setDimensionType(newValue);
        setChartTab(0);
        const dim = DIMENSIONS[newValue];
        setDimensionValue(dim.arrayName && dimensionData?.[dim.arrayName]?.length > 0 ? dimensionData[dim.arrayName][0] : 'All');
    };

    const handleRecalculate = async () => {
        setLoading(true);
        try {
            await axios.post('/api/maintenance/recalculate_metrics');
            handleRefresh();
        } catch (err) {
            console.error('Recalculation failed', err);
            setLoading(false);
        }
    };

    const handleRefresh = () => {
        setLoading(true);
        (async () => {
            try {
                const currentDim = DIMENSIONS[dimensionType];
                if (currentDim.id === 'comparison') {
                    const response = await axios.get(`/api/investment_comparison/${DB_NAME}`);
                    setComparisonData(response.data);
                    setLoading(false);
                    return;
                }
                let filter = currentDim.id;
                if (filter !== 'portfolio') filter = filter === 'investment' ? dimensionValue : `${filter}:${dimensionValue}`;
                const url = currentDim.id === 'investment'
                    ? `/api/investment_metrics_by_name/${DB_NAME}/${encodeURIComponent(filter)}`
                    : `/api/investment_metrics/${DB_NAME}?filter=${encodeURIComponent(filter)}`;
                const response = await axios.get(url);
                setMetricsData(response.data);
            } catch (err) { console.error(err); }
            setLoading(false);
        })();
    };

    const currentDimension = DIMENSIONS[dimensionType];
    const dimensionOptions = currentDimension.arrayName ? (dimensionData?.[currentDimension.arrayName] || []) : [];

    const fmtCurrency = (val: number) => val == null ? 'N/A' : new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR', maximumFractionDigits: 0 }).format(val);
    const fmtPct = (val: number) => val == null ? 'N/A' : `${Number(val).toFixed(2)}%`;
    const fmtDecimal = (val: number) => val == null ? 'N/A' : Number(val).toFixed(4);

    const getLatest = (key: string, field = 'value', fb = 0) => metricsData?.[key]?.length ? (metricsData[key][metricsData[key].length - 1]?.[field] ?? fb) : fb;
    const safeGet = (obj: any, path: string, fb: any = 0) => { let c = obj; for (const k of path.split('.')) { if (c == null) return fb; c = c[k]; } return c ?? fb; };
    const hasData = (k: string) => metricsData?.[k]?.length > 0;
    const hasNested = (p: string, c: string) => metricsData?.[p]?.[c]?.length > 0;

    const makeLine = (k: string, label: string, color: string, vk = 'value') => {
        const d = metricsData?.[k]; if (!d?.length) return null;
        return { labels: d.map((x: any) => x.period), datasets: [{ label, data: d.map((x: any) => x[vk] ?? 0), borderColor: color, backgroundColor: `${color}22`, fill: true, tension: 0.3, pointRadius: 2 }] };
    };
    const makeDual = (k1: string, l1: string, c1: string, k2: string, l2: string, c2: string) => {
        const d1 = metricsData?.[k1], d2 = metricsData?.[k2]; if (!d1?.length && !d2?.length) return null;
        return { labels: (d1 || d2).map((_: any, i: number) => d1?.[i]?.period || d2?.[i]?.period || ''), datasets: [d1?.length ? { label: l1, data: d1.map((x: any) => x.value ?? 0), borderColor: c1, fill: false, tension: 0.3, pointRadius: 2 } : null, d2?.length ? { label: l2, data: d2.map((x: any) => x.value ?? 0), borderColor: c2, fill: false, tension: 0.3, pointRadius: 2 } : null].filter(Boolean) };
    };
    const makeStacked = () => {
        const d = metricsData?.contribution_vs_growth; if (!d?.length) return null;
        return { labels: d.map((x: any) => x.period), datasets: [{ label: 'Growth', data: d.map((x: any) => x.growth ?? 0), backgroundColor: `${CHART_COLORS.green}44`, borderColor: CHART_COLORS.green, fill: true, tension: 0.3, pointRadius: 0 }, { label: 'Contributions', data: d.map((x: any) => x.contributions ?? 0), backgroundColor: `${CHART_COLORS.blue}44`, borderColor: CHART_COLORS.blue, fill: true, tension: 0.3, pointRadius: 0 }] };
    };
    const makeBar = (k: string, label: string, color: string, vk = 'value') => {
        const d = metricsData?.[k]; if (!d?.length) return null;
        return { labels: d.map((x: any) => x.period), datasets: [{ label, data: d.map((x: any) => x[vk] ?? 0), backgroundColor: color, borderColor: color, borderWidth: 1 }] };
    };

    const chartOpts = (yLabel: string, fmt: 'number' | 'percent' = 'number') => ({
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' as const }, title: { display: false }, tooltip: { callbacks: { label: (ctx: any) => fmt === 'percent' ? `${ctx.parsed.y.toFixed(2)}%` : fmtCurrency(ctx.parsed.y) } } },
        scales: { y: { beginAtZero: true, title: { display: true, text: yLabel }, ticks: { callback: (v: any) => fmt === 'percent' ? `${v.toFixed(1)}%` : v.toLocaleString() } }, x: { ticks: { maxTicksLimit: 20, maxRotation: 45 } } }
    });

    const latestCAGR = getLatest('cagr_trend', 'value', 0);
    const latestIRR = getLatest('irr_trend', 'value', 0);
    const latestDividendYield = getLatest('dividend_yield', 'value', 0);
    const volArr = safeGet(metricsData, 'risk_metrics.volatility', []);
    const latestVol = Array.isArray(volArr) && volArr.length ? volArr[volArr.length - 1]?.value || 0 : 0;
    const sharpeArr = safeGet(metricsData, 'risk_metrics.sharpe_ratio', []);
    const latestSharpe = Array.isArray(sharpeArr) && sharpeArr.length ? sharpeArr[sharpeArr.length - 1]?.value || 0 : 0;
    const totalValue = safeGet(metricsData, 'total_current_value') || safeGet(metricsData, 'contribution_vs_growth.0.contributions', 0) + safeGet(metricsData, 'contribution_vs_growth.0.growth', 0);
    const totalReturnAmt = safeGet(metricsData, 'total_return_amount', 0);
    const totalReturnPct = safeGet(metricsData, 'total_return_pct', 0);
    const totalFees = getLatest('fee_analysis', 'total_fees', 0);
    const latestFeeRatio = getLatest('fee_analysis', 'fee_ratio', 0);
    const latestTaxRatio = getLatest('tax_analysis', 'tax_ratio', 0);
    const totalTax = getLatest('tax_analysis', 'total_tax', 0);

    const MetricCard = ({ bg, icon, label, value, sub }: { bg: string; icon: React.ReactNode; label: string; value: React.ReactNode; sub?: React.ReactNode }) => (
        <Card sx={{ borderRadius: 2, background: bg, color: 'white', flex: { xs: '0 0 calc(50% - 8px)', md: '0 0 calc(25% - 12px)' } }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, py: '16px !important' }}>
                {icon}
                <Box><Typography variant="caption" sx={{ opacity: 0.9 }}>{label}</Typography><Typography variant="h6" sx={{ fontWeight: 'bold' }}>{value}</Typography>{sub}</Box>
            </CardContent>
        </Card>
    );

    const MiniCard = ({ label, value, color }: { label: string; value: string; color?: string }) => (
        <Card variant="outlined" sx={{ borderRadius: 2, borderColor: 'divider', flex: { xs: '0 0 calc(50% - 8px)', md: '0 0 calc(20% - 13px)' } }}>
            <CardContent sx={{ py: '12px !important', textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary">{label}</Typography>
                <Typography variant="h6" color={color || 'text.primary'}>{value}</Typography>
            </CardContent>
        </Card>
    );

    const ChartCard = ({ title, chip, chipColor, children }: { title: string; chip?: string; chipColor?: any; children: React.ReactNode }) => (
        <Paper elevation={2} sx={{ p: 2, borderRadius: 3, height: 380, flex: { xs: '0 0 100%', md: '0 0 calc(50% - 12px)' } }}>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>{title}{chip && <Chip label={chip} size="small" sx={{ ml: 1 }} color={chipColor || 'primary'} />}</Typography>
            <Box sx={{ height: 300 }}>{children}</Box>
        </Paper>
    );

    return (
        <ThemeProvider theme={theme}>
            <Box sx={{ bgcolor: 'background.default', minHeight: '100vh', pb: 6, pt: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', px: { xs: 2, md: 3 }, mb: 4, alignItems: 'center' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <DrawerComponent menuItems={menuItems} />
                        <IconButton onClick={() => router.back()} color="inherit" size="large"><KeyboardBackspaceIcon /></IconButton>
                        <Typography variant="h4" sx={{ fontWeight: 'bold', fontSize: { xs: '1.3rem', md: '2rem' } }}>
                            <ShowChartIcon sx={{ mr: 1, verticalAlign: 'middle', fontSize: 36, color: 'primary.main' }} /> Portfolio Metrics
                        </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        <MuiTooltip title="Recalculate all metrics from database">
                            <IconButton onClick={handleRecalculate} color="primary">
                                <BarChartIcon />
                            </IconButton>
                        </MuiTooltip>
                        <MuiTooltip title="Refresh"><IconButton onClick={handleRefresh} color="inherit"><RefreshIcon /></IconButton></MuiTooltip>
                        <IconButton onClick={toggleDarkMode} color="inherit">{darkMode ? <Brightness7Icon /> : <Brightness4Icon />}</IconButton>
                    </Box>
                </Box>

                <Container maxWidth="xl">
                    <Paper elevation={3} sx={{ p: 2, borderRadius: 3, mb: 3 }}>
                        <Tabs value={dimensionType} onChange={handleDimensionChange} variant="scrollable" scrollButtons="auto" textColor="primary" indicatorColor="primary" sx={{ mb: 2 }}>
                            {DIMENSIONS.map(dim => <Tab key={dim.id} label={dim.label} sx={{ fontWeight: 'bold', minHeight: 48 }} />)}
                        </Tabs>
                        {dimensionOptions.length > 0 && currentDimension.id !== 'portfolio' && (
                            <FormControl sx={{ minWidth: 250 }}>
                                <InputLabel>Select {currentDimension.label.replace('By ', '')}</InputLabel>
                                <Select value={dimensionValue} onChange={e => setDimensionValue(e.target.value)} label={`Select ${currentDimension.label.replace('By ', '')}`}>
                                    {dimensionOptions.map((opt: string) => <MenuItem key={opt} value={opt}>{opt}</MenuItem>)}
                                </Select>
                            </FormControl>
                        )}
                    </Paper>

                    {error && !loading && <Alert severity="warning" sx={{ mb: 3, borderRadius: 2 }}>{error}</Alert>}

                    {loading ? (
                        <Box display="flex" justifyContent="center" alignItems="center" py={15} flexDirection="column" gap={2}>
                            <CircularProgress size={60} /><Typography variant="body1" color="text.secondary">Loading metrics...</Typography>
                        </Box>
                    ) : currentDimension.id === 'comparison' ? (
                        <ComparisonView data={comparisonData} fmtCurrency={fmtCurrency} fmtPct={fmtPct} />
                    ) : metricsData ? (
                        <>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 4 }}>
                                <MetricCard bg={METRIC_THEMES.total_value.bg} icon={METRIC_THEMES.total_value.icon} label="Total Value" value={fmtCurrency(totalValue)} />
                                <MetricCard bg={METRIC_THEMES.total_return.bg} icon={totalReturnAmt >= 0 ? METRIC_THEMES.total_return.icon : <TrendingDownIcon sx={{ fontSize: 40 }} />} label="Total Return" value={fmtCurrency(totalReturnAmt)} sub={<Typography variant="caption" sx={{ opacity: 0.8 }}>{fmtPct(totalReturnPct)}</Typography>} />
                                <MetricCard bg={METRIC_THEMES.cagr_irr.bg} icon={METRIC_THEMES.cagr_irr.icon} label="CAGR / IRR" value={`${fmtPct(latestCAGR)} / ${fmtPct(latestIRR)}`} />
                                <MetricCard bg={METRIC_THEMES.total_fees.bg} icon={METRIC_THEMES.total_fees.icon} label="Total Fees" value={fmtCurrency(totalFees)} sub={latestFeeRatio > 0 ? <Typography variant="caption" sx={{ opacity: 0.8 }}>Ratio: {fmtPct(latestFeeRatio)}</Typography> : undefined} />
                            </Box>

                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 4 }}>
                                <MiniCard label="Dividend Yield" value={fmtPct(latestDividendYield)} color="primary.main" />
                                <MiniCard label="Volatility (12m)" value={fmtPct(latestVol)} color={latestVol > 20 ? 'error.main' : latestVol > 10 ? 'warning.main' : 'success.main'} />
                                <MiniCard label="Sharpe Ratio" value={fmtDecimal(latestSharpe)} color={latestSharpe > 1 ? 'success.main' : latestSharpe > 0 ? 'warning.main' : 'error.main'} />
                                <MiniCard label="Tax Ratio" value={fmtPct(latestTaxRatio)} color="error.main" />
                                <MiniCard label="Total Tax" value={fmtCurrency(totalTax)} />
                            </Box>

                            {metricsData.conclusion && (
                                <Paper elevation={1} sx={{ p: 2, borderRadius: 2, mb: 4, bgcolor: 'background.paper' }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}><InfoOutlinedIcon color="info" fontSize="small" /><Typography variant="subtitle2" color="text.secondary">Analysis Summary</Typography></Box>
                                    <Typography variant="body2">{metricsData.conclusion}</Typography>
                                </Paper>
                            )}

                            <Paper elevation={1} sx={{ borderRadius: 2, mb: 2 }}>
                                <Tabs value={chartTab} onChange={(_, v) => setChartTab(v)} variant="scrollable" scrollButtons="auto" textColor="primary" indicatorColor="primary">
                                    {CHART_GROUPS.map(g => <Tab key={g.id} label={g.label} sx={{ fontWeight: 'bold' }} />)}
                                </Tabs>
                            </Paper>

                            {chartTab === 0 && (
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                                    {hasData('portfolio_performance_return') && <ChartCard title="Performance Return Trend" chip="CAGR %" chipColor="primary"><Line data={makeLine('portfolio_performance_return', 'Return %', CHART_COLORS.blue) as any} options={chartOpts('Return %', 'percent') as any} /></ChartCard>}
                                    {hasData('cagr_trend') && <ChartCard title="CAGR Trend Over Time" chip="CAGR" chipColor="secondary"><Line data={makeLine('cagr_trend', 'CAGR %', CHART_COLORS.purple) as any} options={chartOpts('CAGR %', 'percent') as any} /></ChartCard>}
                                    {hasData('irr_trend') && <ChartCard title="IRR Trend Over Time" chip="IRR" chipColor="info"><Line data={makeLine('irr_trend', 'IRR %', CHART_COLORS.orange) as any} options={chartOpts('IRR %', 'percent') as any} /></ChartCard>}
                                    {hasData('contribution_vs_growth') && <ChartCard title="Contribution vs Growth" chip="Stacked" chipColor="success"><Line data={makeStacked() as any} options={chartOpts('Amount') as any} /></ChartCard>}
                                </Box>
                            )}

                            {chartTab === 1 && (
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                                    {hasNested('risk_metrics', 'volatility') && <ChartCard title="Rolling Volatility (12m)" chip="Risk" chipColor="warning"><Line data={makeLine('risk_metrics.volatility', 'Volatility %', CHART_COLORS.orange) as any} options={chartOpts('Volatility %', 'percent') as any} /></ChartCard>}
                                    {hasNested('risk_metrics', 'sharpe_ratio') && <ChartCard title="Sharpe Ratio Over Time" chip="Risk-Adj Return" chipColor="success"><Line data={makeLine('risk_metrics.sharpe_ratio', 'Sharpe Ratio', CHART_COLORS.green) as any} options={chartOpts('Ratio') as any} /></ChartCard>}
                                    {hasData('rolling_returns.one_year') && <ChartCard title="1-Year Rolling Returns"><Line data={makeLine('rolling_returns.one_year', '1Y Return', CHART_COLORS.blue) as any} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } as any} /></ChartCard>}
                                    {hasData('rolling_returns.three_year') && <ChartCard title="3-Year Rolling Returns"><Line data={makeLine('rolling_returns.three_year', '3Y Return', CHART_COLORS.teal) as any} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } as any} /></ChartCard>}
                                    {hasData('rolling_returns.five_year') && <ChartCard title="5-Year Rolling Returns"><Line data={makeLine('rolling_returns.five_year', '5Y Return', CHART_COLORS.purple) as any} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } as any} /></ChartCard>}
                                </Box>
                            )}

                            {chartTab === 2 && (
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                                    {hasData('fee_analysis') && (
                                        <Paper elevation={2} sx={{ p: 2, borderRadius: 3, height: 380, flex: { xs: '0 0 100%', md: '0 0 calc(50% - 12px)' } }}>
                                            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Fee Analysis<Chip label="Cost" size="small" sx={{ ml: 1 }} color="error" /></Typography>
                                            <Box sx={{ height: 160 }}><Line data={makeLine('fee_analysis', 'Fee Ratio %', CHART_COLORS.red, 'fee_ratio') as any} options={chartOpts('Fee Ratio %', 'percent') as any} /></Box>
                                            <Divider sx={{ my: 1 }} />
                                            <Box sx={{ height: 120 }}><Bar data={makeBar('fee_analysis', 'Total Fees', CHART_COLORS.red, 'total_fees') as any} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } as any} /></Box>
                                        </Paper>
                                    )}
                                    {hasData('tax_analysis') && (
                                        <Paper elevation={2} sx={{ p: 2, borderRadius: 3, height: 380, flex: { xs: '0 0 100%', md: '0 0 calc(50% - 12px)' } }}>
                                            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Tax Analysis<Chip label="Cost" size="small" sx={{ ml: 1 }} color="error" /></Typography>
                                            <Box sx={{ height: 160 }}><Line data={makeLine('tax_analysis', 'Tax Ratio %', CHART_COLORS.orange, 'tax_ratio') as any} options={chartOpts('Tax Ratio %', 'percent') as any} /></Box>
                                            <Divider sx={{ my: 1 }} />
                                            <Box sx={{ height: 120 }}><Bar data={makeBar('tax_analysis', 'Total Tax', CHART_COLORS.orange, 'total_tax') as any} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } as any} /></Box>
                                        </Paper>
                                    )}
                                    {hasData('dividend_yield') && <ChartCard title="Dividend Yield Over Time" chip="Income" chipColor="primary"><Line data={makeLine('dividend_yield', 'Dividend Yield', CHART_COLORS.teal) as any} options={chartOpts('Yield %', 'percent') as any} /></ChartCard>}
                                </Box>
                            )}

                            {chartTab === 3 && (
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                                    {hasData('drawdown_analysis') && (
                                        <ChartCard title="Drawdown Analysis" chip="Risk" chipColor="error">
                                            <Line data={makeLine('drawdown_analysis', 'Drawdown', CHART_COLORS.red) as any}
                                                options={{ ...chartOpts('Drawdown %', 'percent'), scales: { y: { beginAtZero: false, title: { display: true, text: 'Drawdown %' } }, x: { ticks: { maxTicksLimit: 15 } } } } as any} />
                                        </ChartCard>
                                    )}
                                    {hasNested('benchmarks', 'portfolio') && hasNested('benchmarks', 'benchmark') && (
                                        <ChartCard title="Portfolio vs Benchmark" chip="Comparison" chipColor="info">
                                            <Line data={makeDual('benchmarks.portfolio', 'Portfolio', CHART_COLORS.blue, 'benchmarks.benchmark', 'Benchmark', CHART_COLORS.grey) as any}
                                                options={{ ...chartOpts('Value', 'percent'), plugins: { legend: { position: 'top' } } } as any} />
                                        </ChartCard>
                                    )}
                                </Box>
                            )}

                            <Box sx={{ mt: 4, textAlign: 'center' }}>
                                <Typography variant="caption" color="text.secondary">
                                    Data source: {metricsData.data_source || 'Simulated'} | Filter: {metricsData.filter_type || 'portfolio'} |
                                    Generated: {metricsData.generated_at ? new Date(metricsData.generated_at).toLocaleString() : 'N/A'}
                                    {metricsData.data_points ? ` | Data points: ${metricsData.data_points}` : ''}
                                </Typography>
                            </Box>
                        </>
                    ) : (
                        <Box display="flex" justifyContent="center" alignItems="center" py={15} flexDirection="column" gap={2}>
                            <ShowChartIcon sx={{ fontSize: 60, color: 'text.disabled' }} />
                            <Typography variant="h6" color="text.secondary">No metrics data available for this selection.</Typography>
                            <Typography variant="body2" color="text.disabled">Try calculating metrics from the maintenance dashboard first.</Typography>
                        </Box>
                    )}
                </Container>
            </Box>
        </ThemeProvider>
    );
}