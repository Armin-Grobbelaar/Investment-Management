"use client";
import { Container, IconButton, Paper, Grid, Typography, Box, Card, CardContent, FormControl, Select, MenuItem, InputLabel, Tabs, Tab, Chip, Alert } from "@mui/material";
import axios from 'axios';
import { useEffect, useState, useMemo, Suspense, lazy } from 'react';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import KeyboardBackspaceIcon from '@mui/icons-material/KeyboardBackspace';
import AssessmentIcon from '@mui/icons-material/Assessment';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import CircularProgress from '@mui/material/CircularProgress';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';
import Link from 'next/link';
import Button from '@mui/material/Button';

// Lazy load heavy components for better initial performance
const LineGraph = lazy(() => import('../Charts/Graphs/LineGraph'));
const AreaChart = lazy(() => import('../Charts/Graphs/AreaChart'));
const ConfidenceIntervalChart = lazy(() => import('../Charts/Graphs/ConfidenceIntervalChart'));

// Prediction model interfaces
interface PredictionModel {
  dates: string[];
  predictions: number[];
  upper_bound: number[];
  lower_bound: number[];
  model_name: string;
  accuracy_score: number;
  risk_level: number;
}

interface PredictionResults {
  [key: string]: PredictionModel | undefined;
  arima?: PredictionModel;
  lstm?: PredictionModel;
  xgboost?: PredictionModel;
  hybrid?: PredictionModel;
  gaussian_process?: PredictionModel;
  auto_arima?: PredictionModel;
}

interface HistoricalData {
  dates: string[];
  prices: number[];
  highs: number[];
  lows: number[];
  volumes: number[];
}

interface PredictionResponse {
  scope: string;
  historical_data: HistoricalData;
  predictions: PredictionResults;
  prediction_horizon_days: number;
  confidence_level: number;
  timestamp: string;
  models_available: number;
  data_quality_score: number;
  quant_metrics?: Record<string, number>; // Added quant metrics
  error?: string;
}

interface ScopeOption {
  value: string;
  label: string;
  description: string;
  color: string;
}

function ViewInvestmentPredictions() {
  const [predictions, setPredictions] = useState<PredictionResponse | null>(null);
  const [darkMode, setDarkMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedScope, setSelectedScope] = useState<string>('portfolio');
  const [selectedModels, setSelectedModels] = useState<string[]>(['arima', 'lstm']);
  const [activeTab, setActiveTab] = useState(0);
  const [predictionMode, setPredictionMode] = useState<'ai' | 'monte_carlo'>('ai');
  const [mcData, setMcData] = useState<any>(null);
  const [mcLoading, setMcLoading] = useState(false);

  const scopeOptions: ScopeOption[] = [
    {
      value: 'portfolio',
      label: 'Entire Portfolio',
      description: 'Predict collective portfolio performance',
      color: '#007FFF'
    },
    {
      value: 'individual',
      label: 'Individual Investments',
      description: 'Analyze specific investment predictions',
      color: '#FF6B35'
    },
    {
      value: 'by_currency',
      label: 'By Currency',
      description: 'Predict currency-grouped performance',
      color: '#00BFFF'
    },
    {
      value: 'by_type',
      label: 'By Investment Type',
      description: 'Forecast by asset class performance',
      color: '#5090D3'
    },
    {
      value: 'by_institution',
      label: 'By Institution',
      description: 'Predict institutional investment trends',
      color: '#66B2FF'
    }
  ];

  const availableModels = [
    { key: 'arima', name: 'ARIMA', description: 'Statistical time series analysis' },
    { key: 'auto_arima', name: 'Auto-ARIMA', description: 'Self-tuning statistical model (pmdarima)' },
    { key: 'lstm', name: 'LSTM Neural Network', description: 'Deep learning for sequential data' },
    { key: 'xgboost', name: 'XGBoost ML', description: 'Machine learning regression' },
    { key: 'hybrid', name: 'Hybrid ARIMA-LSTM', description: 'Combined statistical and deep learning' },
    { key: 'gaussian_process', name: 'Gaussian Process', description: 'Bayesian uncertainty quantification' }
  ];

  useEffect(() => {
    fetchPredictions();
  }, [selectedScope, selectedModels]);

  const fetchPredictions = async () => {
    try {
      setLoading(true);
      console.log(`🔮 Fetching ${getScopeLabel(selectedScope)} predictions for models: ${selectedModels.join(', ')}`);

      const modelFilter = selectedModels.join(',');
      const response = await axios.get(`/api/investment_predictions/Investments?scope=${selectedScope}&model_filter=${modelFilter}`);
      setPredictions(response.data);
      console.log(`✅ Generated predictions for ${response.data.models_available} models`);
    } catch (error) {
      console.error('❌ Error fetching predictions:', error);
      setPredictions(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (predictionMode === 'monte_carlo') {
        fetchMonteCarlo();
    }
  }, [selectedScope, predictionMode]);

  const fetchMonteCarlo = async () => {
    try {
        setMcLoading(true);
        // Map scope to dimension_type/dimension_value
        let dimType = 'portfolio';
        let dimVal = 'All';
        if (selectedScope !== 'portfolio') {
            dimType = selectedScope.replace('by_', 'investment_'); // naive mapping
            // Note: In real app, we need an exact dimension_value.
            // Using a default for now.
        }
        
        const response = await axios.post(`/api/monte_carlo/Investments`, {
            dimension_type: dimType,
            dimension_value: dimVal,
            years: 10,
            num_simulations: 500
        });
        setMcData(response.data);
    } catch (error) {
        console.error('Error fetching Monte Carlo:', error);
    } finally {
        setMcLoading(false);
    }
  };

  const getScopeLabel = (scope: string): string => {
    const option = scopeOptions.find(opt => opt.value === scope);
    return option?.label || 'Portfolio';
  };

  const getScopeDescription = (scope: string): string => {
    const option = scopeOptions.find(opt => opt.value === scope);
    return option?.description || '';
  };

  const getScopeColor = (scope: string): string => {
    const option = scopeOptions.find(opt => opt.value === scope);
    return option?.color || '#007FFF';
  };

  const handleModelToggle = (modelKey: string) => {
    setSelectedModels(prev =>
      prev.includes(modelKey)
        ? prev.filter(m => m !== modelKey)
        : [...prev, modelKey]
    );
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const toggleDarkMode = () => {
    setDarkMode(prevMode => !prevMode);
  };

  const handleBack = () => {
    window.history.back();
  };

  // Prepare data for combined view (historical + predictions)
  const getCombinedChartData = (modelKey: string) => {
    if (!predictions || !predictions.predictions[modelKey]) return [];

    const historical = predictions.historical_data;
    const modelPred = predictions.predictions[modelKey];

    // Convert historical dates and prices
    const historicalPoints = historical.dates.map((date, index) => ({
      x: new Date(date),
      y: historical.prices[index]
    }));

    // Convert prediction dates and values
    const predictionPoints = modelPred.dates.map((date: string, index: number) => ({
      x: new Date(date),
      y: modelPred.predictions[index]
    }));

    // Create upper and lower bound bands
    const upperBoundPoints = modelPred.dates.map((date: string, index: number) => ({
      x: new Date(date),
      y: modelPred.upper_bound[index]
    }));

    const lowerBoundPoints = modelPred.dates.map((date: string, index: number) => ({
      x: new Date(date),
      y: modelPred.lower_bound[index]
    }));

    return [
      {
        label: 'Historical Prices',
        data: historicalPoints,
        borderColour: '#007FFF'
      },
      {
        label: `${modelPred.model_name} Prediction`,
        data: predictionPoints,
        borderColour: '#FF6B35'
      },
      {
        label: 'Prediction Upper Bound',
        data: upperBoundPoints,
        borderColour: '#00BFFF',
        fill: false,
        borderDash: [5, 5]
      },
      {
        label: 'Prediction Lower Bound',
        data: lowerBoundPoints,
        borderColour: '#5090D3',
        fill: false,
        borderDash: [5, 5]
      }
    ];
  };

  // Get accuracy color based on score
  const getAccuracyColor = (score: number): string => {
    if (score >= 0.8) return '#4CAF50'; // Green
    if (score >= 0.6) return '#FF9800'; // Orange
    return '#F44336'; // Red
  };

  const renderModelTab = (modelKey: string) => {
    if (!predictions || !predictions.predictions[modelKey]) {
      return (
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            Model {modelKey.toUpperCase()} not available
          </Typography>
        </Box>
      );
    }

    const model = predictions.predictions[modelKey];
    const chartData = getCombinedChartData(modelKey);

    return (
      <Box sx={{ p: 2 }}>
        <Grid container spacing={3}>
          {/* Model Info Card */}
          <Grid size={{ xs: 12 }}>
            <Card elevation={3} sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {model.model_name} Model Performance
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                  <Chip
                    label={`Accuracy: ${(model.accuracy_score * 100).toFixed(1)}%`}
                    sx={{ bgcolor: getAccuracyColor(model.accuracy_score) }}
                  />
                  <Chip
                    label={`Risk Level: ${model.risk_level.toFixed(2)}`}
                    variant="outlined"
                  />
                  <Typography variant="body2" color="text.secondary">
                    Prediction Horizon: {predictions.prediction_horizon_days} days |
                    Confidence: {(predictions.confidence_level * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Combined Chart */}
          <Grid size={{ xs: 12 }}>
            <Paper elevation={3} sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <TrendingUpIcon sx={{ mr: 1 }} />
                Historical vs {model.model_name} Predictions
              </Typography>
              <Suspense fallback={<div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <CircularProgress size={50} />
                <span style={{ marginLeft: '10px' }}>Loading Prediction Chart...</span>
              </div>}>
                <ConfidenceIntervalChart
                  data={{
                    prediction: model.dates.map((date: string, index: number) => ({
                      x: date,
                      y: model.predictions[index]
                    })),
                    upperBound: model.dates.map((date: string, index: number) => ({
                      x: date,
                      y: model.upper_bound[index]
                    })),
                    lowerBound: model.dates.map((date: string, index: number) => ({
                      x: date,
                      y: model.lower_bound[index]
                    })),
                    historical: predictions.historical_data.dates.map((date: string, index: number) => ({
                      x: date,
                      y: predictions.historical_data.prices[index]
                    }))
                  }}
                  title={`${getScopeLabel(selectedScope)} Price Forecast - ${model.model_name}`}
                  theme={darkMode ? 'dark' : 'light'}
                />
              </Suspense>
            </Paper>
          </Grid>

          {/* Confidence Interval Visualization */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper elevation={3} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Confidence Interval (95% Uncertainty Range)
              </Typography>
              <Suspense fallback={<div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <CircularProgress size={40} />
                <span style={{ marginLeft: '10px' }}>Loading Confidence Chart...</span>
              </div>}>
                <ConfidenceIntervalChart
                  data={{
                    prediction: model.dates.map((date: string, index: number) => ({
                      x: date,
                      y: model.predictions[index]
                    })),
                    upperBound: model.dates.map((date: string, index: number) => ({
                      x: date,
                      y: model.upper_bound[index]
                    })),
                    lowerBound: model.dates.map((date: string, index: number) => ({
                      x: date,
                      y: model.lower_bound[index]
                    })),
                    historical: predictions.historical_data.dates.slice(-10).map((date: string, index: number) => {
                      const historicalIndex = predictions.historical_data.dates.length - 10 + index;
                      return {
                        x: date,
                        y: predictions.historical_data.prices[historicalIndex]
                      };
                    })
                  }}
                  title={`${model.model_name} Confidence Bounds`}
                  theme={darkMode ? 'dark' : 'light'}
                />
              </Suspense>
            </Paper>
          </Grid>

          {/* Model Statistics */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper elevation={3} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Model Insights & Analytics
              </Typography>
              <Box sx={{ display: 'grid', gap: 2 }}>
                <Box>
                  <Typography variant="subtitle2" color="primary">
                    Trend Direction
                  </Typography>
                  <Typography variant="body1">
                    {model.predictions[model.predictions.length - 1] > predictions.historical_data.prices[predictions.historical_data.prices.length - 1]
                      ? '📈 Bullish (Expected increase)'
                      : '📉 Bearish (Expected decrease)'}
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" color="primary">
                    Prediction Range
                  </Typography>
                  <Typography variant="body1">
                    ${(Math.min(...model.predictions)).toFixed(2)} - ${(Math.max(...model.predictions)).toFixed(2)}
                    ({((Math.max(...model.predictions) - Math.min(...model.predictions)) / Math.min(...model.predictions) * 100).toFixed(1)}% range)
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" color="primary">
                    Confidence Interval Width
                  </Typography>
                  <Typography variant="body1">
                    Average: {((model.upper_bound.reduce((a: number, b: number) => a + b) - model.lower_bound.reduce((a: number, b: number) => a + b)) / model.dates.length / predictions.historical_data.prices[predictions.historical_data.prices.length - 1] * 100).toFixed(1)}%
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" color="primary">
                    Model Type
                  </Typography>
                  <Typography variant="body1">
                    {modelKey === 'arima' ? 'Statistical Time Series' :
                      modelKey === 'lstm' ? 'Deep Learning Neural Network' :
                        modelKey === 'xgboost' ? 'Gradient Boosting Ensemble' :
                          modelKey === 'hybrid' ? 'Statistical + Deep Learning' :
                            'Bayesian Regression'}
                  </Typography>
                </Box>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    );
  };

  if (loading && !predictions) {
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
              Generating AI Predictions for {getScopeLabel(selectedScope)}...
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Analyzing historical data with {selectedModels.length} prediction models
            </Typography>
          </div>
        </div>
      </ThemeProvider>
    );
  }

  if (!predictions) {
    return (
      <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
        <div style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh' }}>
          <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
            {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
          </IconButton>
          <Container maxWidth="xl" sx={{ py: 4 }}>
            <Typography variant="h5" color="error">
              Unable to load investment predictions. Please try again later.
            </Typography>
          </Container>
        </div>
      </ThemeProvider>
    );
  }

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
                  <Typography variant="h3" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                    <AssessmentIcon sx={{ mr: 2, color: getScopeColor(selectedScope) }} />
                    AI Investment Predictions
                  </Typography>
                  <Typography variant="subtitle1" color="text.secondary" gutterBottom>
                    Data-driven forecasts using advanced machine learning models
                  </Typography>

                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                    <Tabs value={predictionMode} onChange={(_e, v) => setPredictionMode(v)} textColor="primary" indicatorColor="primary">
                        <Tab value="ai" label="Machine Learning AI" />
                        <Tab value="monte_carlo" label="Monte Carlo Simulation" />
                    </Tabs>
                  </Box>

                  {/* Scope Selector */}
                  <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
                    <FormControl variant="outlined" sx={{ minWidth: 280 }}>
                      <InputLabel id="scope-select-label">Analysis Scope</InputLabel>
                      <Select
                        labelId="scope-select-label"
                        id="scope-select"
                        value={selectedScope}
                        onChange={(e) => setSelectedScope(e.target.value)}
                        label="Analysis Scope"
                        disabled={loading}
                      >
                        {scopeOptions.map((option) => (
                          <MenuItem key={option.value} value={option.value}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Box sx={{
                                width: 12,
                                height: 12,
                                borderRadius: '50%',
                                bgcolor: option.color
                              }} />
                              <Box>
                                <Typography variant="subtitle2">{option.label}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {option.description}
                                </Typography>
                              </Box>
                            </Box>
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    {/* Model Selection Chips */}
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ mr: 1 }}>Models:</Typography>
                      {availableModels.map((model) => (
                        <Chip
                          key={model.key}
                          label={model.name}
                          size="small"
                          onClick={() => handleModelToggle(model.key)}
                          color={selectedModels.includes(model.key) ? "primary" : "default"}
                          variant={selectedModels.includes(model.key) ? "filled" : "outlined"}
                          disabled={loading}
                        />
                      ))}
                    </Box>
                  </Box>

                  {/* Results Summary */}
                  {predictionMode === 'ai' ? (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                      <strong>{getScopeLabel(selectedScope)} Analysis:</strong> {predictions?.models_available || 0} AI models generated {predictions?.prediction_horizon_days || 0}-day forecasts
                      with {((predictions?.confidence_level || 0.95) * 100).toFixed(0)}% confidence intervals.
                      Data quality score: {((predictions?.data_quality_score || 0.95) * 100).toFixed(0)}%
                    </Typography>
                  </Alert>
                  ) : (
                  <Alert severity="success" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                        <strong>Monte Carlo Analysis:</strong> 500 geometric brownian motion simulations over 10 years.
                        Projected median value: {mcData?.final_stats?.median ? new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR' }).format(mcData.final_stats.median) : '...'}
                    </Typography>
                  </Alert>
                  )}
                </Box>
                <ShowChartIcon sx={{ fontSize: '3rem', color: 'primary.main', ml: 3 }} />
              </Box>
            </Grid>
          </Grid>

          {/* Loading indicator for scope/model changes */}
          {loading && (
            <Grid container spacing={3} sx={{ mb: 4 }}>
              <Grid size={{ xs: 12 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 2 }}>
                  <CircularProgress size={40} />
                  <Typography variant="body1" sx={{ ml: 2 }}>
                    Recalculating predictions for {getScopeLabel(selectedScope)} with selected models...
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          )}

          {/* Model Tabs or Monte Carlo */}
          {!loading && (
            predictionMode === 'monte_carlo' ? (
                <Grid container spacing={3}>
                    <Grid size={12}>
                        <Paper elevation={3} sx={{ p: 3 }}>
                            <Typography variant="h6" gutterBottom>Monte Carlo Fan Chart</Typography>
                            {mcLoading || !mcData ? (
                                <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}><CircularProgress /></Box>
                            ) : (
                                <Box sx={{ height: 500 }}>
                                    <Suspense fallback={<CircularProgress />}>
                                        <LineGraph 
                                            data={[
                                                { label: "p95", data: mcData.percentiles.p95.map((v:any, i:any) => ({ x: i, y: v })), borderColour: "#4caf50", fill: false, borderDash: [5,5] },
                                                { label: "p75", data: mcData.percentiles.p75.map((v:any, i:any) => ({ x: i, y: v })), borderColour: "#8bc34a", fill: false },
                                                { label: "Median", data: mcData.percentiles.p50.map((v:any, i:any) => ({ x: i, y: v })), borderColour: "#2196f3", fill: false },
                                                { label: "p25", data: mcData.percentiles.p25.map((v:any, i:any) => ({ x: i, y: v })), borderColour: "#ff9800", fill: false },
                                                { label: "p5", data: mcData.percentiles.p5.map((v:any, i:any) => ({ x: i, y: v })), borderColour: "#f44336", fill: false, borderDash: [5,5] }
                                            ]}
                                            title="10-Year Monte Carlo Simulation"
                                            theme={darkMode ? 'dark' : 'light'}
                                        />
                                    </Suspense>
                                </Box>
                            )}
                        </Paper>
                    </Grid>
                </Grid>
            ) : (
            <Paper elevation={3} sx={{ width: '100%', mb: 4 }}>
              <Tabs
                value={activeTab}
                onChange={handleTabChange}
                variant="scrollable"
                scrollButtons="auto"
                sx={{ borderBottom: 1, borderColor: 'divider' }}
              >
                {selectedModels.map((modelKey, index) => {
                  const modelInfo = availableModels.find(m => m.key === modelKey);
                  const prediction = predictions?.predictions?.[modelKey];
                  return (
                    <Tab
                      key={modelKey}
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle2">{modelInfo?.name}</Typography>
                          {prediction && (
                            <Chip
                              size="small"
                              label={`${(prediction.accuracy_score * 100).toFixed(0)}%`}
                              sx={{
                                bgcolor: getAccuracyColor(prediction.accuracy_score),
                                color: 'white',
                                fontSize: '0.7rem'
                              }}
                            />
                          )}
                        </Box>
                      }
                      sx={{ minHeight: 48 }}
                    />
                  );
                })}
              </Tabs>

              {selectedModels.map((modelKey, index) => (
                <div key={modelKey} hidden={activeTab !== index}>
                  {renderModelTab(modelKey)}
                </div>
              ))}
            </Paper>
            )
          )}

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
              <Button variant="outlined" color="secondary" size="large">
                Main Dashboard
              </Button>
            </Link>
            <Link href="/ViewInvestmentMetrics" passHref>
              <Button variant="contained" color="primary" size="large">
                View Metrics
              </Button>
            </Link>
          </Box>
        </Container>
      </div>
    </ThemeProvider>
  );
}

export default ViewInvestmentPredictions;
