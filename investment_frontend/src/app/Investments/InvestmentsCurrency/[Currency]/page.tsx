"use client";
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Container, IconButton, Paper, Grid, Typography, Card, CardContent } from "@mui/material";
import axios from 'axios';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '../../../Themes/muiTheme';
import CircularProgress from '@mui/material/CircularProgress';
import DrawerComponent from '../../../Reusable Components/Drawers/SideMenyDrawer';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
const LineGraph = lazy(() => import('../../../Charts/Graphs/LineGraph'));
const PieChart = lazy(() => import('../../../Charts/Graphs/PieChart'));
const StickyHeadTable = lazy(() => import('../../../Charts/Tables/StickyHeadTable'));
import { Suspense, lazy } from 'react';

interface KeyMetric {
  metric: string;
  value: number;
  unit: string;
  formatted_value: string;
}

interface MenuItem {
  heading: string;
  items: string[];
  urls: string[];
}

interface InvestmentSummaryInterface {
  id: number;
  investment_type?: string;
  institution_name?: string;
  investment_name: string;
  unit_currency?: string;
  investment_value_in_native_currency: number;
  unit_price_in_native_currency: number;
  total_units_held: number;
  initial_unit_price_in_native_currency: number;
  initial_investment_date: string;
}

const summary_table_columns = [
  { id: 'investment_name', label: 'Investment Name', minWidth: 170 },
  { id: 'investment_value_in_native_currency', label: "Value in R", minWidth: 100 },
  { id: 'unit_price_in_native_currency', label: "Unit Price in R", minWidth: 100 },
  { id: 'total_units_held', label: 'Total Units Held', minWidth: 100 },
  { id: "initial_unit_price_in_native_currency", label: "Initial Unit Price in R", minWidth: 100 },
  { id: "initial_investment_date", label: "Initial Investment Date", minWidth: 100 },
];

export default function FilteredCurrencyPage() {
  const params = useParams();
  const filterValue = decodeURIComponent(params.Currency as string);
  const [darkMode, setDarkMode] = useState(false);
  const [AllInvestmentValues, setAllInvestmentValues] = useState<any[]>([]);
  const [AllInvestmentPieValues, setAllInvestmentPieValues] = useState<any>(null);
  const [InvestmentSummary, setInvestmentSummary] = useState<InvestmentSummaryInterface[]>([]);
  const [OtherPieValues, setOtherPieValues] = useState<any>(null);
  const [OtherTableRows, setOtherTableRows] = useState<any[]>([]);
  const [keyMetrics, setKeyMetrics] = useState<KeyMetric[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [minDate, setMinDate] = useState<Date>();
  const [maxDate, setMaxDate] = useState<Date>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchFilteredData() {
      try {
        setLoading(true);
        console.log(`🚀 Fetching filtered investment data for currency: ${filterValue}`);

        const response = await axios.get(
          `/api/dashboard_charts/Investments?filter_type=unit_currency&filter_value=${encodeURIComponent(filterValue)}`
        );

        const chartData = response.data;
        const dateRange = chartData.timeseries_date_range || {};
        const minDate = dateRange.min ? new Date(dateRange.min) : new Date('2023-01-01');
        const maxDate = dateRange.max ? new Date(dateRange.max) : new Date();

        setAllInvestmentValues(chartData.timeseries || []);
        setAllInvestmentPieValues(chartData.individual_pie || null);
        setInvestmentSummary(chartData.summary_table || []);
        setOtherPieValues(chartData.institution_pie || null);
        setOtherTableRows(chartData.institution_table || []);
        setKeyMetrics(chartData.key_metrics || []);
        setMenuItems(chartData.menu_items || []);
        setMinDate(minDate);
        setMaxDate(maxDate);

        console.log(`💰 Filtered portfolio shows ${chartData.summary_table?.length || 0} ${filterValue} investments`);

      } catch (error) {
        console.error('❌ Error fetching filtered data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchFilteredData();
  }, [filterValue]);

  const toggleDarkMode = () => {
    setDarkMode(prevMode => !prevMode);
  };

  if (loading) {
    return (
      <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
        <div style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
            {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
          </IconButton>
          <div style={{ textAlign: 'center' }}>
            <CircularProgress size={50} />
            <Typography variant="h6" style={{ marginTop: '20px' }}>
              Loading {filterValue} Investments...
            </Typography>
          </div>
        </div>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
      <div style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh' }}>
        <DrawerComponent menuItems={menuItems} />
        <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
          {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
        </IconButton>
        <Container maxWidth="xl" sx={{ py: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom align="center" sx={{ mb: 3 }}>
            {filterValue} Currency Investments
          </Typography>

          {keyMetrics.length > 0 && (
            <Grid container spacing={2} sx={{ mb: 4 }}>
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
            </Grid>
          )}

          <Grid container spacing={3}>
            <Grid size={{ xs: 12 }}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Suspense fallback={<div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircularProgress size={50} /><span style={{ marginLeft: '10px' }}>Loading Chart...</span>
                </div>}>
                  <LineGraph data={AllInvestmentValues} minDate={minDate} maxDate={maxDate}
                    title={`Value Trends - ${filterValue} Investments`} xAxisLabel="Date" yAxisLabel="Value in R" />
                </Suspense>
              </Paper>
            </Grid>
            <Grid size={{ xs: 12 }}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Suspense fallback={<div style={{ height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircularProgress size={30} /><span style={{ marginLeft: '10px' }}>Loading Table...</span>
                </div>}>
                  <StickyHeadTable columns={summary_table_columns} rows={InvestmentSummary ?? []} />
                </Suspense>
              </Paper>
            </Grid>
            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                  <CircularProgress size={40} /><span style={{ marginTop: '10px' }}>Loading Chart...</span>
                </div>}>
                  <PieChart data={AllInvestmentPieValues} title="Investment Breakdown" theme={darkMode ? 'dark' : 'light'} />
                </Suspense>
              </Paper>
            </Grid>
            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={3} sx={{ p: 3, height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                  <CircularProgress size={40} /><span style={{ marginTop: '10px' }}>Loading Chart...</span>
                </div>}>
                  <PieChart data={OtherPieValues} title="By Institution" theme={darkMode ? 'dark' : 'light'} />
                </Suspense>
              </Paper>
            </Grid>
            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Suspense fallback={<div style={{ height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircularProgress size={30} /><span style={{ marginLeft: '10px' }}>Loading Table...</span>
                </div>}>
                  <StickyHeadTable
                    columns={[
                      { id: "institution_name", label: "Institution", minWidth: 150 },
                      { id: "investment_value_in_native_currency", label: "Value in R", minWidth: 100 },
                      { id: "initial_investment_date", label: "Earliest Investment", minWidth: 100 }
                    ]}
                    rows={OtherTableRows}
                  />
                </Suspense>
              </Paper>
            </Grid>
          </Grid>
        </Container>
      </div>
    </ThemeProvider>
  );
}
