"use client";
import { Container, IconButton, Paper, Grid, Typography, Box, Card, CardContent, FormControl, Select, MenuItem, InputLabel } from "@mui/material";
import axios from 'axios';
import { useEffect, useState, useMemo, Suspense, lazy } from 'react';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import KeyboardBackspaceIcon from '@mui/icons-material/KeyboardBackspace';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import CircularProgress from '@mui/material/CircularProgress';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';
import Link from 'next/link';
import Button from '@mui/material/Button';

// Lazy load heavy components for better initial performance
const LineGraph = lazy(() => import('../Charts/Graphs/LineGraph'));
const PieChart = lazy(() => import('../Charts/Graphs/PieChart'));
const AreaChart = lazy(() => import('../Charts/Graphs/AreaChart'));

// Metric data interfaces
interface Metric {
  period: string;
  value: number;
  index: number;
}

interface InvestmentMetrics {
  portfolio_performance_return: Metric[];
  rolling_returns: {
    one_year: Metric[];
    three_year: Metric[];
    five_year: Metric[];
  };
  risk_metrics: {
    volatility: Metric[];
    sharpe_ratio: Metric[];
  };
  contribution_vs_growth: Metric[];
  drawdown_analysis: Metric[];
  benchmarks: {
    portfolio: Metric[];
    benchmark: Metric[];
  };
  dividend_yield: Metric[];
  conclusion: string;
}

interface FilterOption {
  value: string;
  label: string;
  description: string;
}

function ViewInvestmentMetrics() {
  const [metrics, setMetrics] = useState<InvestmentMetrics | null>(null);
  const [darkMode, setDarkMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState<string>('portfolio');

  const filterOptions: FilterOption[] = [
    {
      value: 'portfolio',
      label: 'Entire Portfolio',
      description: 'Comprehensive analysis of your complete investment portfolio performance over time'
    },
    {
      value: 'individual',
      label: 'Individual Investments',
      description: 'Analyze performance metrics for specific individual investments'
    },
    {
      value: 'by_currency',
      label: 'By Currency',
      description: 'View metrics grouped by investment currency (ZAR, USD, EUR, etc.)'
    },
    {
      value: 'by_type',
      label: 'By Investment Type',
      description: 'Analyze performance metrics by investment type (Stocks, Bonds, ETFs, etc.)'
    },
    {
      value: 'by_institution',
      label: 'By Institution',
      description: 'View metrics grouped by financial institutions and brokers'
    }
  ];

  const getFilterDescription = (filterValue: string): string => {
    const option = filterOptions.find(opt => opt.value === filterValue);
    return option?.description || 'Select a filter option for detailed analysis';
  };

  const getFilterLabel = (filterValue: string): string => {
    const option = filterOptions.find(opt => opt.value === filterValue);
    return option?.label || 'Entire Portfolio';
  };

  useEffect(() => {
    async function fetchInvestmentMetrics() {
      try {
        setLoading(true);
        console.log(`📊 Fetching ${getFilterLabel(selectedFilter).toLowerCase()} metrics data...`);

        // Add filter parameter to the URL
        const response = await axios.get(`http://192.168.10.100:3337/investment_metrics/Investments?filter=${selectedFilter}`);
        setMetrics(response.data);
        console.log('✅ Investment metrics loaded successfully');
      } catch (error) {
        console.error('❌ Error fetching metrics:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchInvestmentMetrics();
  }, [selectedFilter]);

  const handleFilterChange = (event: any) => {
    setSelectedFilter(event.target.value);
  };

  const toggleDarkMode = () => {
    setDarkMode(prevMode => !prevMode);
  };

  const handleBack = () => {
    window.history.back();
  };

  if (loading && !metrics) {
    return (
      <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
        <div style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh' }}>
          <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
            {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
          </IconButton>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh'
          }}>
            <CircularProgress size={60} />
            <Typography variant="h6" sx={{ mt: 2 }}>
              Analyzing {getFilterLabel(selectedFilter)} Metrics...
            </Typography>
          </div>
        </div>
      </ThemeProvider>
    );
  }

  if (!metrics) {
    return (
      <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
        <div style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh' }}>
          <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
            {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
          </IconButton>
          <Container maxWidth="xl" sx={{ py: 4 }}>
            <Typography variant="h5" color="error">
              Unable to load investment metrics. Please try again later.
            </Typography>
          </Container>
        </div>
      </ThemeProvider>
    );
  }

  // Transform data for charts
  const portfolioReturnData = metrics.portfolio_performance_return.map(point => ({
    label: `${getFilterLabel(selectedFilter)} Performance`,
    data: [{
      x: new Date(Date.now() - (metrics.portfolio_performance_return.length - point.index) * 24 * 60 * 60 * 1000),
      y: point.value
    }],
    borderColour: '#007FFF'
  }));

  const volatilityData = metrics.risk_metrics.volatility.map(point => ({
    x: new Date(Date.now() - (metrics.risk_metrics.volatility.length - point.index) * 24 * 60 * 60 * 1000),
    y: point.value * 100 // Convert to percentage
  }));

  const riskAdjustedData = [
    {
      label: 'Volatility (Annualized %)',
      data: volatilityData,
      borderColour: '#FF6B35'
    }
  ];

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
      <div style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh', transition: 'background-color 0.3s' }}>
        <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
          {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
        </IconButton>

        <Container maxWidth="xl" sx={{ py: 4 }}>
          {/* Header */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid size={{ xs: 12 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h3" component="h1" gutterBottom>
                    Investment Metrics Dashboard
                  </Typography>
                  <Typography variant="subtitle1" color="text.secondary" gutterBottom>
                    {getFilterDescription(selectedFilter)}
                  </Typography>

                  {/* Filter Dropdown */}
                  <FormControl variant="outlined" sx={{ minWidth: 280, mt: 2 }}>
                    <InputLabel id="filter-select-label">Analysis Scope</InputLabel>
                    <Select
                      labelId="filter-select-label"
                      id="filter-select"
                      value={selectedFilter}
                      onChange={handleFilterChange}
                      label="Analysis Scope"
                      disabled={loading}
                    >
                      {filterOptions.map((option) => (
                        <MenuItem key={option.value} value={option.value}>
                          <Box>
                            <Typography variant="subtitle2">{option.label}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {option.description}
                            </Typography>
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
                <ShowChartIcon sx={{ fontSize: '3rem', color: 'primary.main', ml: 3 }} />
              </Box>
            </Grid>
          </Grid>

          {/* Loading indicator for filter changes */}
          {loading && (
            <Grid container spacing={3} sx={{ mb: 4 }}>
              <Grid size={{ xs: 12 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 2 }}>
                  <CircularProgress size={40} />
                  <Typography variant="body1" sx={{ ml: 2 }}>
                    Updating analysis for {getFilterLabel(selectedFilter).toLowerCase()}...
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          )}

          {/* Portfolio Performance Overview */}
          <Grid container spacing={3}>
            {/* Portfolio Performance Over Time */}
            <Grid size={{ xs: 12 }}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <ShowChartIcon sx={{ mr: 1 }} />
                  {getFilterLabel(selectedFilter)} Performance Return
                </Typography>
                <Suspense fallback={<div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircularProgress size={50} />
                  <span style={{ marginLeft: '10px' }}>Loading Performance Data...</span>
                </div>}>
                  <LineGraph
                    data={portfolioReturnData}
                    minDate={new Date(Date.now() - 365 * 24 * 60 * 60 * 1000)}
                    maxDate={new Date()}
                    title={`${getFilterLabel(selectedFilter)} Value Growth (%)`}
                    xAxisLabel="Date"
                    yAxisLabel="Return %"
                  />
                </Suspense>
              </Paper>
            </Grid>

            {/* Risk Metrics */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Risk Analysis - {getFilterLabel(selectedFilter)}
                </Typography>
                <Suspense fallback={<div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircularProgress size={40} />
                  <span style={{ marginLeft: '10px' }}>Loading Risk Data...</span>
                </div>}>
                  <LineGraph
                    data={riskAdjustedData}
                    minDate={new Date(Date.now() - 180 * 24 * 60 * 60 * 1000)}
                    maxDate={new Date()}
                    title={`${getFilterLabel(selectedFilter)} Volatility`}
                    xAxisLabel="Date"
                    yAxisLabel="Volatility %"
                  />
                </Suspense>
              </Paper>
            </Grid>

            {/* Rolling Returns */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Rolling Returns Summary - {getFilterLabel(selectedFilter)}
                </Typography>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 4 }}>
                    <Card sx={{ bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                      <CardContent sx={{ textAlign: 'center', py: 2 }}>
                        <Typography variant="h6" component="div">
                          1 Year
                        </Typography>
                        <Typography variant="h4" component="div" sx={{ fontWeight: 'bold' }}>
                          {metrics.rolling_returns.one_year.length > 0
                            ? `${metrics.rolling_returns.one_year[metrics.rolling_returns.one_year.length - 1].value.toFixed(1)}%`
                            : 'N/A'
                          }
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid size={{ xs: 4 }}>
                    <Card sx={{ bgcolor: 'success.light', color: 'success.contrastText' }}>
                      <CardContent sx={{ textAlign: 'center', py: 2 }}>
                        <Typography variant="h6" component="div">
                          3 Year
                        </Typography>
                        <Typography variant="h4" component="div" sx={{ fontWeight: 'bold' }}>
                          {metrics.rolling_returns.three_year.length > 0
                            ? `${metrics.rolling_returns.three_year[metrics.rolling_returns.three_year.length - 1].value.toFixed(1)}%`
                            : 'N/A'
                          }
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid size={{ xs: 4 }}>
                    <Card sx={{ bgcolor: 'secondary.light', color: 'secondary.contrastText' }}>
                      <CardContent sx={{ textAlign: 'center', py: 2 }}>
                        <Typography variant="h6" component="div">
                          5 Year
                        </Typography>
                        <Typography variant="h4" component="div" sx={{ fontWeight: 'bold' }}>
                          {metrics.rolling_returns.five_year.length > 0
                            ? `${metrics.rolling_returns.five_year[metrics.rolling_returns.five_year.length - 1].value.toFixed(1)}%`
                            : 'N/A'
                          }
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Paper>
            </Grid>

            {/* Dividend Yield Over Time */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  {getFilterLabel(selectedFilter)} Dividend Yield Trend
                </Typography>
                <Suspense fallback={<div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircularProgress size={40} />
                  <span style={{ marginLeft: '10px' }}>Loading Dividend Data...</span>
                </div>}>
                  <LineGraph
                    data={[{
                      label: `${getFilterLabel(selectedFilter)} Dividend Yield`,
                      data: metrics.dividend_yield.map(point => ({
                        x: new Date(Date.now() - (metrics.dividend_yield.length - point.index) * 30 * 24 * 60 * 60 * 1000),
                        y: point.value * 100 // Convert to percentage
                      })),
                      borderColour: '#00BFFF'
                    }]}
                    minDate={new Date(Date.now() - 365 * 24 * 60 * 60 * 1000)}
                    maxDate={new Date()}
                    title={`${getFilterLabel(selectedFilter)} Dividend Yield`}
                    xAxisLabel="Date"
                    yAxisLabel="Yield %"
                  />
                </Suspense>
              </Paper>
            </Grid>

            {/* Drawdown Analysis */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  {getFilterLabel(selectedFilter)} Drawdown Analysis
                </Typography>
                <Suspense fallback={<div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircularProgress size={40} />
                  <span style={{ marginLeft: '10px' }}>Loading Drawdown Data...</span>
                </div>}>
                  <AreaChart
                    data={{
                      datasets: [{
                        label: `${getFilterLabel(selectedFilter)} Drawdown`,
                        data: metrics.drawdown_analysis.map(point => ({
                          x: new Date(Date.now() - (metrics.drawdown_analysis.length - point.index) * 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                          y: Math.abs(point.value) * 100 // Convert to positive percentage
                        })),
                        fill: true,
                        backgroundColor: '#FF6B4030',
                        borderColor: '#FF6B35',
                        pointRadius: 0
                      }]
                    }}
                    title={`${getFilterLabel(selectedFilter)} Drawdowns`}
                    theme={darkMode ? 'dark' : 'light'}
                  />
                </Suspense>
              </Paper>
            </Grid>
          </Grid>

          {/* Navigation Buttons */}
          <Box sx={{
            mt: 6,
            display: 'flex',
            justifyContent: 'center',
            gap: 3
          }}>
            <Button
              variant="outlined"
              startIcon={<KeyboardBackspaceIcon />}
              onClick={handleBack}
              size="large"
            >
              Back to Investments
            </Button>
            <Link href="/Investments" passHref>
              <Button variant="contained" color="primary" size="large">
                Main Dashboard
              </Button>
            </Link>
          </Box>
        </Container>
      </div>
    </ThemeProvider>
  );
}

export default ViewInvestmentMetrics;
