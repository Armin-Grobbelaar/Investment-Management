"use client";
import React, { useEffect, useState, Suspense, lazy } from 'react';
import { Container, IconButton, Paper, Grid, Typography, Box, Card, CardContent, Button, CircularProgress } from "@mui/material";
import axios from 'axios';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';
import Link from 'next/link';

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

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        setIsLoaded(false);
        setLoadError(null);

        let endpoint = "/api/dashboard_charts/Investments";
        if (filterType && filterValue) {
          endpoint += `?filter_type=${encodeURIComponent(filterType)}&filter_value=${encodeURIComponent(filterValue)}`;
        }

        console.log(`🚀 Fetching dashboard data from ${endpoint}...`);
        const response = await axios.get(endpoint, { timeout: 30000 });
        const chartData = response.data;

        const dateRange = chartData.timeseries_date_range || {};
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
  }, [filterType, filterValue]);

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
                <Button variant="contained" onClick={() => window.location.reload()}>🔄 Retry</Button>
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
