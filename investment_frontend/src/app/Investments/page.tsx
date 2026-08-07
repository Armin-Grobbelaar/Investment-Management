"use client";
import { Container, IconButton, Paper, Grid, Typography, Box, Card, CardContent, Button } from "@mui/material";
import axios from 'axios';
import { useEffect, useState, useMemo, Suspense, lazy } from 'react';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import CircularProgress from '@mui/material/CircularProgress';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';
import Link from 'next/link';

// Lazy load heavy components for better initial performance
const LineGraph = lazy(() => import('../Charts/Graphs/LineGraph'));
const PieChart = lazy(() => import('../Charts/Graphs/PieChart'));
const BarChart = lazy(() => import('../Charts/Graphs/BarChart'));
const AreaChart = lazy(() => import('../Charts/Graphs/AreaChart'));
const StickyHeadTable = lazy(() => import('../Charts/Tables/StickyHeadTable'));

interface Point {
  x: Date;
  y: number;
};

interface LineGraphData {
  label: string;
  data: Point[];
  borderColour: string;
};

interface PieChartData {
  labels: string[];
  datasets: {
    data: number[];
    backgroundColor: string[];
  }[];
}

// Optimized interfaces for the new API endpoints
interface DashboardData {
  investment_summary: InvestmentSummaryInterface[];
  portfolio_totals: PortfolioTotals;
  currencies_in_portfolio: string[];
  types_in_portfolio: string[];
  base_currency: string;
  timestamp: string;
  cache_expires_in: number;
}

interface TimeseriesData {
  timeseries: LineGraphData[];
  date_range: {
    min: string;
    max: string;
  };
  base_currency: string;
  total_investments: number;
}

interface PortfolioTotals {
  total_value: number;
  by_currency: { [key: string]: number };
  by_type: { [key: string]: number };
  base_currency: string;
  count_investments: number;
}

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

interface InvestmentTypeTableRowsInterface {
  id: number;
  investment_type: string;
  investment_value_in_native_currency: number;
  initial_investment_date: string;
};

interface InvestmentCurrencyTableRowsInterface {
  id: number;
  unit_currency: string;
  investment_value_in_native_currency: number;
  initial_investment_date: string;
};

interface InvestmentInstitutionTableRowsInterface {
  id: number;
  institution_name: string;
  investment_value_in_native_currency: number;
  initial_investment_date: string;
};

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

const investment_summary_table_columns = [
  { id: 'investment_name', label: 'Investment Name', minWidth: 170 },
  { id: 'investment_type', label: 'Investment Type', minWidth: 100 },
  //{ id: 'unit_currency', label: 'Unit Currency', minWidth: 100 },
  //{id: "exchange_rate", label: "Exchange Rate", minWidth: 170},
  { id: "investment_value_in_native_currency", label: "Investment Value in R", minWidth: 100},
  { id: "unit_price_in_native_currency", label: "Unit Price in R", minWidth: 100},
  { id: 'total_units_held', label: 'Total Units Held', minWidth: 100 },
  { id: "initial_unit_price_in_native_currency", label: "Initial Unit Price in R", minWidth: 100},
  { id: "initial_investment_date", label: "Initial Investment Date", minWidth: 100},
];

const investment_type_table_columns =[
  {id: "investment_type", label: "Investment Type", minWidth: 50},
  {id: "investment_value_in_native_currency", label: "Investment Value in R", minWidth: 50},
  {id: "initial_investment_date", label: "Initial Investment Date", minWidth: 50}
];

const investment_currency_table_columns =[
  {id: "unit_currency", label: "Investment Currency", minWidth: 50},
  {id: "investment_value_in_native_currency", label: "Investment Value in R", minWidth: 50},
  {id: "initial_investment_date", label: "Initial Investment Date", minWidth: 50}
];

const investment_institution_table_columns =[
  {id: "institution_name", label: "Institution's Name", minWidth: 50},
  {id: "investment_value_in_native_currency", label: "Investment Value in R", minWidth: 50},
  {id: "initial_investment_date", label: "Initial Investment Date", minWidth: 50}
];

const getRandomColor = () => {
  const letters = '0123456789ABCDEF';
  let color = '#';
  for (let i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
};


function AllInvestments() {
  const [AllInvestmentValues, setAllInvestmentValues] = useState<LineGraphData[] | null>(null);
  const [AllInvestmentPieValues, setAllInvestmentPieValues] = useState<PieChartData | null>(null);
  const [InvestmentSummary, setInvestmentSummary] = useState<InvestmentSummaryInterface[] | null>(null);
  const [InvestmentTypePieValues, setInvestmentTypePieValues] = useState<PieChartData | null>(null);
  const [InvestmentTypeTableRows, setInvestmentTypeTableRows] = useState<InvestmentTypeTableRowsInterface[] | null>(null);
  const [InvestmentCurrencyPieValues, setInvestmentCurrencyPieValues] = useState<PieChartData | null>(null);
  const [InvestmentCurrencyTableRows, setInvestmentCurrencyTableRows] = useState<InvestmentCurrencyTableRowsInterface[] | null>(null);
  const [InvestmentInsitutionPieValues, setInvestmentInstitutionPieValues] = useState<PieChartData | null>(null);
  const [InvestmentInsitutionTableRows, setInvestmentInstitutionTableRows] = useState<InvestmentInstitutionTableRowsInterface[] | null>(null);
  const [barCharts, setBarCharts] = useState<any[]>([]);
  const [areaCharts, setAreaCharts] = useState<any[]>([]);
  const [keyMetrics, setKeyMetrics] = useState<KeyMetric[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [minDate, setMinDate] = useState<Date>();
  const [maxDate, setMaxDate] = useState<Date>();
  const [darkMode, setDarkMode] = useState(false);
  const [visibleDatasets, setVisibleDatasets] = useState<LineGraphData[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchServerProcessedData() {
      try {
        console.log('🚀 Fetching dashboard data...');
        const response = await axios.get("/api/dashboard_charts/Investments", { timeout: 30000 });
        const chartData = response.data;

        const dateRange = chartData.timeseries_date_range || {};
        const minDate = dateRange.min ? new Date(dateRange.min) : new Date('2023-01-01');
        const maxDate = dateRange.max ? new Date(dateRange.max) : new Date();

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
        setMinDate(minDate);
        setMaxDate(maxDate);
        setIsLoaded(true);
        console.log('✅ Dashboard loaded');
      } catch (error: any) {
        console.error('❌ Error fetching dashboard data:', error);
        const msg = error?.response?.data?.detail || error?.message || 'Unknown error';
        setLoadError(`Failed to load dashboard: ${msg}`);
      }
    }
    fetchServerProcessedData();
  }, []);

  const handleVisibilityChange = (visibleDatasets: LineGraphData[]) => {
    console.log('📊 Visibility change detected:', visibleDatasets.length, 'datasets visible');

    if (visibleDatasets.length > 0 && AllInvestmentValues) {
      // Find the earliest and latest dates from visible datasets only
      let earliestDate = new Date('2100-01-01');
      let latestDate = new Date('1900-01-01');

      visibleDatasets.forEach(dataset => {
        dataset.data.forEach(point => {
          const date = new Date(point.x);
          if (date < earliestDate) earliestDate = date;
          if (date > latestDate) latestDate = date;
        });
      });

      console.log('📅 Recalculated date range from visible datasets:');
      console.log('   Min:', earliestDate.toISOString(), 'Max:', latestDate.toISOString());

      setMinDate(earliestDate);
      setMaxDate(latestDate);
      setVisibleDatasets(visibleDatasets);
    } else {
      // If no datasets visible, use original range
      const dateRange = minDate?.toISOString() || '2023-01-01';
      setVisibleDatasets([]);
      console.log('⚠️ No visible datasets, using original date range');
    }
  };

  const toggleDarkMode = () => {
    setDarkMode(prevMode => !prevMode);
  };

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
      <div>
        {isLoaded ? (
          <div style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh', transition: 'background-color 0.3s' }}>
            <DrawerComponent menuItems={menuItems} />
            <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
              {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>
            <Container maxWidth="xl" sx={{ py: 4 }}>
              <Grid container spacing={3}>
                {/* Key Metrics Tiles - Dynamic based on server data */}
                {keyMetrics.map((metric, index) => (
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }} key={index}>
                    <Card elevation={3} sx={{ height: '120px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h6" component="div" gutterBottom color="primary">
                          {metric.metric}
                        </Typography>
                        <Typography variant="h4" component="div" gutterBottom sx={{ fontWeight: 'bold' }}>
                          {metric.formatted_value}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}

                {/* Line Graph - Full Width - Lazy Loaded */}
                <Grid size={{ xs: 12 }}>
                  <Paper elevation={3} sx={{ p: 3 }}>
                    <Suspense fallback={<div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <CircularProgress size={50} />
                      <span style={{ marginLeft: '10px' }}>Loading Line Chart...</span>
                    </div>}>
                      <LineGraph
                        data={AllInvestmentValues}
                        minDate={minDate}
                        maxDate={maxDate}
                        title="Investment values"
                        xAxisLabel="Date"
                        yAxisLabel="Value in R"
                        onVisibilityChange={handleVisibilityChange}
                      />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Investment Summary Table - Full Width - Lazy Loaded */}
                <Grid size={{ xs: 12 }}>
                  <Paper elevation={3} sx={{ p: 3 }}>
                    <Suspense fallback={<div style={{ height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <CircularProgress size={30} />
                      <span style={{ marginLeft: '10px' }}>Loading Investment Summary...</span>
                    </div>}>
                      <StickyHeadTable columns={investment_summary_table_columns} rows={InvestmentSummary ?? []} />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Section Heading: Individual Investments */}
                <Grid size={{ xs: 12 }}>
                  <Typography variant="h5" component="h2" gutterBottom sx={{ mt: 3, mb: 2, fontWeight: 'bold' }}>
                    Individual Investment Values
                  </Typography>
                </Grid>

                {/* Individual Investment Section - Pie Chart */}
                <Grid size={{ xs: 12, lg: 6 }}>
                  <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                      <CircularProgress size={40} />
                      <span style={{ marginTop: '10px' }}>Loading Individual Investments...</span>
                    </div>}>
                      <PieChart data={AllInvestmentPieValues ?? { labels: [], datasets: [] }} title="Individual Investment Values" theme={darkMode ? 'dark' : 'light'} />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Section Heading: By Investment Type */}
                <Grid size={{ xs: 12 }}>
                  <Typography variant="h5" component="h2" gutterBottom sx={{ mt: 3, mb: 2, fontWeight: 'bold' }}>
                    Investment Values by Type
                  </Typography>
                </Grid>

                {/* Investment Type Pie Chart - LEFT */}
                <Grid size={{ xs: 12, lg: 6 }}>
                  <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                      <CircularProgress size={40} />
                      <span style={{ marginTop: '10px' }}>Loading Type Chart...</span>
                    </div>}>
                      <PieChart data={InvestmentTypePieValues} title="" theme={darkMode ? 'dark' : 'light'} />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Investment Type Table - RIGHT */}
                <Grid size={{ xs: 12, lg: 6 }}>
                  <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', flexDirection: 'column' }}>
                    <Suspense fallback={<div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <CircularProgress size={30} />
                      <span style={{ marginLeft: '10px' }}>Loading Type Table...</span>
                    </div>}>
                      <StickyHeadTable columns={investment_type_table_columns} rows={InvestmentTypeTableRows ?? []} />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Section Heading: By Currency */}
                <Grid size={{ xs: 12 }}>
                  <Typography variant="h5" component="h2" gutterBottom sx={{ mt: 3, mb: 2, fontWeight: 'bold' }}>
                    Investment Values by Currency
                  </Typography>
                </Grid>

                {/* Investment Currency Pie Chart - LEFT */}
                <Grid size={{ xs: 12, lg: 6 }}>
                  <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                      <CircularProgress size={40} />
                      <span style={{ marginTop: '10px' }}>Loading Currency Chart...</span>
                    </div>}>
                      <PieChart data={InvestmentCurrencyPieValues} title="" theme={darkMode ? 'dark' : 'light'} />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Investment Currency Table - RIGHT */}
                <Grid size={{ xs: 12, lg: 6 }}>
                  <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', flexDirection: 'column' }}>
                    <Suspense fallback={<div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <CircularProgress size={30} />
                      <span style={{ marginLeft: '10px' }}>Loading Currency Table...</span>
                    </div>}>
                      <StickyHeadTable columns={investment_currency_table_columns} rows={InvestmentCurrencyTableRows ?? []} />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Section Heading: By Institution */}
                <Grid size={{ xs: 12 }}>
                  <Typography variant="h5" component="h2" gutterBottom sx={{ mt: 3, mb: 2, fontWeight: 'bold' }}>
                    Investment Values by Institution
                  </Typography>
                </Grid>

                {/* Investment Institution Pie Chart - LEFT */}
                <Grid size={{ xs: 12, lg: 6 }}>
                  <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                      <CircularProgress size={40} />
                      <span style={{ marginTop: '10px' }}>Loading Institution Chart...</span>
                    </div>}>
                      <PieChart data={InvestmentInsitutionPieValues} title="" theme={darkMode ? 'dark' : 'light'} />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Investment Institution Table - RIGHT */}
                <Grid size={{ xs: 12, lg: 6 }}>
                  <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', flexDirection: 'column' }}>
                    <Suspense fallback={<div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <CircularProgress size={30} />
                      <span style={{ marginLeft: '10px' }}>Loading Institution Table...</span>
                    </div>}>
                      <StickyHeadTable columns={investment_institution_table_columns} rows={InvestmentInsitutionTableRows ?? []} />
                    </Suspense>
                  </Paper>
                </Grid>

                {/* Bar Charts */}
                {barCharts && Array.isArray(barCharts) && barCharts.length > 0 && barCharts.map((barChart, index) => (
                  <Grid size={{ xs: 12, lg: 6 }} key={`bar-${index}`}>
                    <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                        <CircularProgress size={40} />
                        <span style={{ marginTop: '10px' }}>Loading Bar Chart...</span>
                      </div>}>
                        <BarChart data={barChart.data} title={barChart?.title || `Bar Chart ${index + 1}`} type={barChart?.type || 'verticalBar'} theme={darkMode ? 'dark' : 'light'} />
                      </Suspense>
                    </Paper>
                  </Grid>
                ))}

                {/* Area Charts */}
                {areaCharts && Array.isArray(areaCharts) && areaCharts.length > 0 && areaCharts.map((areaChart, index) => (
                  <Grid size={{ xs: 12, lg: 6 }} key={`area-${index}`}>
                    <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                        <CircularProgress size={40} />
                        <span style={{ marginTop: '10px' }}>Loading Area Chart...</span>
                      </div>}>
                        <AreaChart data={areaChart.data} title={areaChart?.title || `Area Chart ${index + 1}`} theme={darkMode ? 'dark' : 'light'} />
                      </Suspense>
                    </Paper>
                  </Grid>
                ))}
              </Grid>

              {/* Bottom Buttons - At the bottom of page content */}
              <Box sx={{
                mt: 4,
                display: 'flex',
                justifyContent: 'center',
                gap: 2,
                flexWrap: 'wrap'
              }}>
                <Link href="/NetWorth" passHref>
                  <Button variant="contained" color="success" size="large" sx={{ minWidth: 160 }}>
                    💰 Net Worth
                  </Button>
                </Link>
                <Link href="/IRRAnalysis" passHref>
                  <Button variant="contained" size="large" sx={{ minWidth: 140, background: 'linear-gradient(135deg,#007FFF,#0054a8)' }}>
                    📈 IRR Analysis
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
                  <Button variant="outlined" size="large" sx={{ minWidth: 120 }}>
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
          </div>
        ) : (
          <div style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', transition: 'background-color 0.3s' }}>
            <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
              {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>
            {loadError ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <Typography variant="h5" color="error" gutterBottom>⚠️ Dashboard Error</Typography>
                <Typography variant="body1" color="textSecondary" sx={{ mb: 3, maxWidth: 500 }}>{loadError}</Typography>
                <Button variant="contained" onClick={() => window.location.reload()}>🔄 Retry</Button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <CircularProgress />
                <Typography variant="body1">Loading Investment Data...</Typography>
              </div>
            )}
          </div>
        )}
      </div>
    </ThemeProvider>
  );
}

export default AllInvestments;
