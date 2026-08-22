"use client";
import React, { useEffect, useState, Suspense, lazy } from 'react';
import {
  Container, IconButton, Paper, Grid, Typography, Box, Card, CardContent,
  Button, CircularProgress, Select, MenuItem as MuiMenuItem, FormControl, InputLabel
} from "@mui/material";
import axios from 'axios';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

// Lazy load heavy chart components
const LineGraph = lazy(() => import('../Charts/Graphs/LineGraph'));
const PieChart = lazy(() => import('../Charts/Graphs/PieChart'));
const BarChart = lazy(() => import('../Charts/Graphs/BarChart'));
const AreaChart = lazy(() => import('../Charts/Graphs/AreaChart'));
const StickyHeadTable = lazy(() => import('../Charts/Tables/StickyHeadTable'));

interface InvestmentSummaryInterface {
  id: number;
  institution_name: string;
  investment_name: string;
  investment_type: string;
  unit_currency: string;
  investment_value: number;
  unit_price: number;
  total_units_held: number;
  initial_unit_price: number;
  initial_investment_date: string;
  display_currency?: string;
  investment_value_in_native_currency?: number;
  unit_price_in_native_currency?: number;
  initial_unit_price_in_native_currency?: number;
}

interface MenuItem {
  heading: string;
  items: string[];
  urls: string[];
}

interface KeyMetric {
  metric: string;
  value: number;
  unit: string;
  formatted_value: string;
}

const summary_table_columns = [
  { id: 'investment_name', label: 'Investment Name', minWidth: 170 },
  { id: 'investment_type', label: 'Investment Type', minWidth: 100 },
  { id: "investment_value_in_native_currency", label: "Value in R", minWidth: 100 },
  { id: "unit_price_in_native_currency", label: "Unit Price in R", minWidth: 100 },
  { id: 'total_units_held', label: 'Total Units Held', minWidth: 100 },
  { id: "initial_unit_price_in_native_currency", label: "Initial Unit Price in R", minWidth: 100 },
  { id: "initial_investment_date", label: "Initial Investment Date", minWidth: 100 },
];

const type_table_columns = [
  { id: "investment_type", label: "Investment Type", minWidth: 100 },
  { id: "investment_value_in_native_currency", label: "Value in R", minWidth: 100 },
  { id: "initial_investment_date", label: "Initial Investment Date", minWidth: 100 }
];

const currency_table_columns = [
  { id: "unit_currency", label: "Currency", minWidth: 100 },
  { id: "investment_value_in_native_currency", label: "Value in R", minWidth: 100 },
  { id: "initial_investment_date", label: "Initial Investment Date", minWidth: 100 }
];

const institution_table_columns = [
  { id: "institution_name", label: "Institution", minWidth: 120 },
  { id: "investment_value_in_native_currency", label: "Value in R", minWidth: 100 },
  { id: "initial_investment_date", label: "Initial Investment Date", minWidth: 100 }
];

interface DashboardProps {
  filterType?: string;
  filterValue?: string;
}

export default function InvestmentsDashboard({ filterType, filterValue }: DashboardProps) {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [AllInvestmentValues, setAllInvestmentValues] = useState<any[] | null>(null);
  const [AllInvestmentPieValues, setAllInvestmentPieValues] = useState<any | null>(null);
  const [InvestmentSummary, setInvestmentSummary] = useState<InvestmentSummaryInterface[] | null>(null);
  const [InvestmentTypePieValues, setInvestmentTypePieValues] = useState<any | null>(null);
  const [InvestmentTypeTableRows, setInvestmentTypeTableRows] = useState<any[] | null>(null);
  const [InvestmentCurrencyPieValues, setInvestmentCurrencyPieValues] = useState<any | null>(null);
  const [InvestmentCurrencyTableRows, setInvestmentCurrencyTableRows] = useState<any[] | null>(null);
  const [InvestmentInstitutionPieValues, setInvestmentInstitutionPieValues] = useState<any | null>(null);
  const [InvestmentInstitutionTableRows, setInvestmentInstitutionTableRows] = useState<any[] | null>(null);
  const [barCharts, setBarCharts] = useState<any[]>([]);
  const [areaCharts, setAreaCharts] = useState<any[]>([]);
  const [keyMetrics, setKeyMetrics] = useState<KeyMetric[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [minDate, setMinDate] = useState<Date>();
  const [maxDate, setMaxDate] = useState<Date>();
  const [darkMode, setDarkMode] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [baseCurrency, setBaseCurrency] = useState<string>("ZAR");
  const [availableCurrencies, setAvailableCurrencies] = useState<string[]>([]);
  const [currenciesLoaded, setCurrenciesLoaded] = useState(false);
  const [dbName, setDbName] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/LoginPage');
    } else if (status === 'authenticated') {
      setDbName((session as any)?.database_name || "Investments");
    }
  }, [status, router, session]);

  // Sync theme with localStorage
  useEffect(() => {
    const saved = localStorage.getItem('theme_mode');
    if (saved) {
      setDarkMode(saved === 'dark');
    }
  }, []);

  const toggleDarkMode = () => {
    setDarkMode(prev => {
      const next = !prev;
      localStorage.setItem('theme_mode', next ? 'dark' : 'light');
      return next;
    });
  };

  // Fetch available currencies on mount
  useEffect(() => {
    async function fetchCurrencies() {
      try {
        const res = await axios.get("/api/currencies");
        const currencies = res.data?.currencies || ["ZAR", "USD", "EUR", "GBP"];
        setAvailableCurrencies(currencies);
        // Use first available currency as default, or ZAR if available
        const defaultCurrency = currencies.includes("ZAR") ? "ZAR" : currencies[0];
        setBaseCurrency(defaultCurrency);
      } catch (err) {
        console.warn("Failed to fetch currencies, using defaults:", err);
        setAvailableCurrencies(["ZAR", "USD", "EUR", "GBP"]);
        setBaseCurrency("ZAR");
      } finally {
        setCurrenciesLoaded(true);
      }
    }
    fetchCurrencies();
  }, []);

  useEffect(() => {
    if (!dbName) return;
    async function fetchDashboardData() {
      try {
        setIsLoaded(false);
        setLoadError(null);

        let endpoint = `/api/dashboard_charts/${dbName}`;
        const params = new URLSearchParams();
        if (filterType && filterValue) {
          params.set("filter_type", filterType);
          params.set("filter_value", filterValue);
        }
        params.set("base_currency", baseCurrency);
        if ([...params].length) {
          endpoint += `?${params.toString()}`;
        }

        console.log(`🚀 Fetching dashboard data from ${endpoint}...`);
        const response = await axios.get(endpoint, { timeout: 30000 });
        const chartData = response.data;

        if (!chartData || typeof chartData !== 'object') {
          throw new Error('Server returned an empty or invalid response');
        }

        const dateRange = chartData.timeseries_date_range || { min: null, max: null };
        const parsedMin = dateRange.min ? new Date(dateRange.min) : new Date('2023-01-01');
        const parsedMax = dateRange.max ? new Date(dateRange.max) : new Date();

        setAllInvestmentValues(chartData.timeseries || []);
        setAllInvestmentPieValues(chartData.individual_pie || { labels: [], datasets: [] });
        setInvestmentSummary(chartData.summary_table || []);
        setInvestmentTypePieValues(chartData.type_pie || { labels: [], datasets: [] });
        setInvestmentTypeTableRows(chartData.type_table || []);
        setInvestmentCurrencyPieValues(chartData.currency_pie || { labels: [], datasets: [] });
        setInvestmentCurrencyTableRows(chartData.currency_table || []);
        setInvestmentInstitutionPieValues(chartData.institution_pie || { labels: [], datasets: [] });
        setInvestmentInstitutionTableRows(chartData.institution_table || []);
        setBarCharts(chartData.bar_charts || []);
        setAreaCharts(chartData.area_charts || []);
        setKeyMetrics(chartData.key_metrics || []);
        setMenuItems(chartData.menu_items || []);
        setMinDate(parsedMin);
        setMaxDate(parsedMax);
        setIsLoaded(true);
        console.log('✅ Dashboard data loaded successfully');
      } catch (error: any) {
        console.error('❌ Error fetching dashboard data:', error);
        const msg = error?.response?.data?.detail || error?.message || 'Unknown error';
        setLoadError(`Failed to load dashboard: ${msg}`);
      }
    }

    fetchDashboardData();
  }, [filterType, filterValue, baseCurrency, dbName]);

  const isEmpty = isLoaded && (!InvestmentSummary || InvestmentSummary.length === 0);
  const displayTitle = filterValue ? `${filterValue} Investments` : "All Investments";

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
      <div style={{ backgroundColor: darkMode ? '#001E3C' : '#f8fafc', minHeight: '100vh', transition: 'background-color 0.3s' }}>
        {isLoaded ? (
          <Box sx={{ pb: 6 }}>
            <DrawerComponent menuItems={menuItems} />
            <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '12px', right: '16px', zIndex: 10 }}>
              {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>

            <Box sx={{ position: 'absolute', top: '12px', right: '60px', zIndex: 10, display: 'flex', alignItems: 'center' }}>
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <Select
                  value={baseCurrency}
                  onChange={(e) => setBaseCurrency(e.target.value)}
                  sx={{
                    color: darkMode ? '#fff' : 'inherit',
                    '& .MuiOutlinedInput-notchedOutline': { borderColor: darkMode ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.2)' },
                    height: '35px'
                  }}
                >
                  {availableCurrencies.map(c => (
                    <MuiMenuItem key={c} value={c}>{c}</MuiMenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>

            {/* ── Empty-state screen ── */}
            {isEmpty ? (
              <Box
                sx={{
                  minHeight: '100vh',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  px: 3,
                  textAlign: 'center',
                }}
              >
                {/* Icon / illustration */}
                <Box
                  sx={{
                    width: 120,
                    height: 120,
                    borderRadius: '50%',
                    background: darkMode
                      ? 'linear-gradient(135deg, rgba(0,127,255,0.25), rgba(0,84,168,0.15))'
                      : 'linear-gradient(135deg, rgba(0,127,255,0.12), rgba(0,84,168,0.06))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    mb: 3,
                    border: '2px dashed',
                    borderColor: 'primary.main',
                    opacity: 0.85,
                  }}
                >
                  <Typography sx={{ fontSize: 52, lineHeight: 1 }}>📊</Typography>
                </Box>

                <Typography variant="h4" component="h1" sx={{ fontWeight: 700, mb: 1 }}>
                  Your Portfolio is Empty
                </Typography>
                <Typography
                  variant="body1"
                  color="textSecondary"
                  sx={{ maxWidth: 480, mb: 4, lineHeight: 1.7 }}
                >
                  No investments found yet. Add your first investment manually or import
                  multiple investments at once using the Bulk Import tool.
                </Typography>

                {/* Primary CTA */}
                <Link href="/AddInvestment" passHref>
                  <Button
                    id="empty-state-add-investment-btn"
                    variant="contained"
                    size="large"
                    startIcon={<AddCircleOutlineIcon />}
                    sx={{
                      mb: 2,
                      px: 5,
                      py: 1.5,
                      fontSize: '1.05rem',
                      fontWeight: 700,
                      borderRadius: 3,
                      background: 'linear-gradient(135deg, #007FFF, #0054a8)',
                      boxShadow: '0 4px 20px rgba(0,127,255,0.35)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #0069d9, #004291)',
                        boxShadow: '0 6px 24px rgba(0,127,255,0.45)',
                        transform: 'translateY(-1px)',
                      },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    Add Your First Investment
                  </Button>
                </Link>

                {/* Secondary CTA */}
                <Link href="/BulkImport" passHref>
                  <Button
                    id="empty-state-bulk-import-btn"
                    variant="outlined"
                    size="large"
                    startIcon={<UploadFileIcon />}
                    sx={{
                      mb: 4,
                      px: 5,
                      py: 1.5,
                      fontSize: '1rem',
                      fontWeight: 600,
                      borderRadius: 3,
                      borderWidth: 2,
                      '&:hover': { borderWidth: 2, transform: 'translateY(-1px)' },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    Bulk Import Investments
                  </Button>
                </Link>

                {/* Tip note */}
                <Paper
                  elevation={0}
                  sx={{
                    maxWidth: 520,
                    px: 3,
                    py: 2,
                    borderRadius: 2,
                    border: '1px solid',
                    borderColor: darkMode ? 'rgba(0,127,255,0.3)' : 'rgba(0,127,255,0.2)',
                    backgroundColor: darkMode ? 'rgba(0,127,255,0.08)' : 'rgba(0,127,255,0.04)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 1.5,
                    textAlign: 'left',
                  }}
                >
                  <Typography sx={{ fontSize: 20, mt: 0.2 }}>💡</Typography>
                  <Typography variant="body2" color="textSecondary" sx={{ lineHeight: 1.65 }}>
                    <strong>Tip:</strong> Have many investments? Use{' '}
                    <Link href="/BulkImport" passHref style={{ color: 'inherit', fontWeight: 600 }}>
                      Bulk Import
                    </Link>{' '}
                    to upload a CSV or spreadsheet and add them all at once — saving you time
                    compared to adding each one individually.
                  </Typography>
                </Paper>
              </Box>
            ) : (

            <Container maxWidth="xl" sx={{ py: 4 }}>
              {/* Header Title */}
              <Typography variant="h4" component="h1" align="center" sx={{ mb: 3, fontWeight: 'bold' }}>
                {displayTitle}
              </Typography>

              <Grid container spacing={3}>
                {/* Key Metrics Tiles */}
                {keyMetrics.map((metric, index) => (
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }} key={index}>
                    <Card elevation={3} sx={{ height: '120px', display: 'flex', flexDirection: 'column', justifyContent: 'center', borderRadius: 2 }}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="body2" color="textSecondary" gutterBottom>
                          {metric.metric}
                        </Typography>
                        <Typography variant="h4" component="div" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                          {metric.formatted_value}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}

                {/* Line Graph - Main Performance Chart */}
                <Grid size={{ xs: 12 }}>
                  <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
                    <Suspense fallback={<Box sx={{ height: '350px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><CircularProgress /></Box>}>
                      <LineGraph
                        data={AllInvestmentValues}
                        minDate={minDate}
                        maxDate={maxDate}
                        title={`Value Trends - ${displayTitle}`}
                        xAxisLabel="Date"
                        yAxisLabel="Value in R"
                      />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Investment Summary Table */}
                <Grid size={{ xs: 12 }}>
                  <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
                      Investment Breakdown Summary
                    </Typography>
                    <Suspense fallback={<Box sx={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><CircularProgress /></Box>}>
                      <StickyHeadTable columns={summary_table_columns} rows={InvestmentSummary ?? []} />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Individual Investment Breakdown Chart */}
                <Grid size={{ xs: 12, lg: 6 }}>
                  <Paper elevation={3} sx={{ p: 3, minHeight: '420px', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold', textAlign: 'center' }}>
                      Individual Investment Holdings
                    </Typography>
                    <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Suspense fallback={<CircularProgress />}>
                        <PieChart data={AllInvestmentPieValues} theme={darkMode ? 'dark' : 'light'} />
                      </Suspense>
                    </Box>
                  </Paper>
                </Grid>

                {/* Type Pie Chart */}
                {InvestmentTypePieValues?.labels?.length > 0 && (
                  <Grid size={{ xs: 12, lg: 6 }}>
                    <Paper elevation={3} sx={{ p: 3, minHeight: '420px', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold', textAlign: 'center' }}>
                        Allocation by Investment Type
                      </Typography>
                      <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Suspense fallback={<CircularProgress />}>
                          <PieChart data={InvestmentTypePieValues} theme={darkMode ? 'dark' : 'light'} />
                        </Suspense>
                      </Box>
                    </Paper>
                  </Grid>
                )}

                {/* Type Table */}
                {InvestmentTypeTableRows && InvestmentTypeTableRows.length > 0 && (
                  <Grid size={{ xs: 12, lg: 6 }}>
                    <Paper elevation={3} sx={{ p: 3, minHeight: '420px', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
                        Type Breakdown Table
                      </Typography>
                      <StickyHeadTable columns={type_table_columns} rows={InvestmentTypeTableRows} />
                    </Paper>
                  </Grid>
                )}

                {/* Currency Pie Chart */}
                {InvestmentCurrencyPieValues?.labels?.length > 0 && (
                  <Grid size={{ xs: 12, lg: 6 }}>
                    <Paper elevation={3} sx={{ p: 3, minHeight: '420px', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold', textAlign: 'center' }}>
                        Allocation by Currency
                      </Typography>
                      <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Suspense fallback={<CircularProgress />}>
                          <PieChart data={InvestmentCurrencyPieValues} theme={darkMode ? 'dark' : 'light'} />
                        </Suspense>
                      </Box>
                    </Paper>
                  </Grid>
                )}

                {/* Currency Table */}
                {InvestmentCurrencyTableRows && InvestmentCurrencyTableRows.length > 0 && (
                  <Grid size={{ xs: 12, lg: 6 }}>
                    <Paper elevation={3} sx={{ p: 3, minHeight: '420px', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
                        Currency Breakdown Table
                      </Typography>
                      <StickyHeadTable columns={currency_table_columns} rows={InvestmentCurrencyTableRows} />
                    </Paper>
                  </Grid>
                )}

                {/* Institution Pie Chart */}
                {InvestmentInstitutionPieValues?.labels?.length > 0 && (
                  <Grid size={{ xs: 12, lg: 6 }}>
                    <Paper elevation={3} sx={{ p: 3, minHeight: '420px', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold', textAlign: 'center' }}>
                        Allocation by Institution
                      </Typography>
                      <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Suspense fallback={<CircularProgress />}>
                          <PieChart data={InvestmentInstitutionPieValues} theme={darkMode ? 'dark' : 'light'} />
                        </Suspense>
                      </Box>
                    </Paper>
                  </Grid>
                )}

                {/* Institution Table */}
                {InvestmentInstitutionTableRows && InvestmentInstitutionTableRows.length > 0 && (
                  <Grid size={{ xs: 12, lg: 6 }}>
                    <Paper elevation={3} sx={{ p: 3, minHeight: '420px', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
                        Institution Breakdown Table
                      </Typography>
                      <StickyHeadTable columns={institution_table_columns} rows={InvestmentInstitutionTableRows} />
                    </Paper>
                  </Grid>
                )}

                {/* Bar Charts */}
                {barCharts && Array.isArray(barCharts) && barCharts.map((barChart, index) => (
                  <Grid size={{ xs: 12, lg: 6 }} key={`bar-${index}`}>
                    <Paper elevation={3} sx={{ p: 3, minHeight: '420px', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
                      <Suspense fallback={<CircularProgress />}>
                        <BarChart data={barChart.data} title={barChart?.title || `Bar Chart ${index + 1}`} type={barChart?.type || 'verticalBar'} theme={darkMode ? 'dark' : 'light'} />
                      </Suspense>
                    </Paper>
                  </Grid>
                ))}

                {/* Area Charts */}
                {areaCharts && Array.isArray(areaCharts) && areaCharts.map((areaChart, index) => (
                  <Grid size={{ xs: 12, lg: 6 }} key={`area-${index}`}>
                    <Paper elevation={3} sx={{ p: 3, minHeight: '420px', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
                      <Suspense fallback={<CircularProgress />}>
                        <AreaChart data={areaChart.data} title={areaChart?.title || `Area Chart ${index + 1}`} theme={darkMode ? 'dark' : 'light'} />
                      </Suspense>
                    </Paper>
                  </Grid>
                ))}
              </Grid>

              {/* Bottom Action Navigation Buttons */}
              <Box sx={{ mt: 5, display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
                <Link href="/Factsheets" passHref>
                  <Button variant="contained" color="info" size="large" sx={{ minWidth: 150 }}>
                    📄 Factsheets
                  </Button>
                </Link>
                <Link href="/NetWorth" passHref>
                  <Button variant="contained" color="success" size="large" sx={{ minWidth: 150 }}>
                    💰 Net Worth
                  </Button>
                </Link>
                <Link href="/IRRAnalysis" passHref>
                  <Button variant="contained" size="large" sx={{ minWidth: 150, background: 'linear-gradient(135deg,#007FFF,#0054a8)' }}>
                    📈 IRR Analysis
                  </Button>
                </Link>
                <Link href="/PropertyAnalysis" passHref>
                  <Button variant="contained" color="secondary" size="large" sx={{ minWidth: 170 }}>
                    🏠 Property Analysis
                  </Button>
                </Link>
                <Link href="/ViewInvestmentPredictions" passHref>
                  <Button variant="contained" color="primary" size="large" sx={{ minWidth: 160 }}>
                    🔮 View Predictions
                  </Button>
                </Link>
                <Link href="/ViewInvestmentMetrics" passHref>
                  <Button variant="outlined" color="secondary" size="large" sx={{ minWidth: 140 }}>
                    📊 View Metrics
                  </Button>
                </Link>
                <Link href="/EditInvestmentData" passHref>
                  <Button variant="outlined" size="large" sx={{ minWidth: 130 }}>
                    ✏️ Edit Data
                  </Button>
                </Link>
                <Link href="/BulkImport" passHref>
                  <Button variant="outlined" color="primary" size="large" sx={{ minWidth: 140 }}>
                    📥 Bulk Import
                  </Button>
                </Link>
              </Box>

            </Container>
            )}
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
            <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '12px', right: '16px' }}>
              {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>
            {loadError ? (
              <Box sx={{ textAlign: 'center', p: 4 }}>
                <Typography variant="h5" color="error" gutterBottom>⚠️ Dashboard Error</Typography>
                <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>{loadError}</Typography>
                <Link href="/AddInvestment" passHref>
                  <Button variant="contained" size="large" startIcon={<AddCircleOutlineIcon />} sx={{ mr: 2 }}>
                    Add Investment
                  </Button>
                </Link>
                <Button variant="outlined" onClick={() => window.location.reload()}>🔄 Retry</Button>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <CircularProgress />
                <Typography variant="body1">Loading Investment Dashboard...</Typography>
              </Box>
            )}
          </Box>
        )}
      </div>
    </ThemeProvider>
  );
}
