'use client';

import React, { useState, useEffect } from 'react';
import {
    Container,
    Paper,
    Button,
    IconButton,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Box,
    Typography,
    Grid,
    Chip,
    Card,
    CardContent,
    CardActions,
    Fab,
    Tooltip,
    Alert
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import CloseIcon from '@mui/icons-material/Close';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip as ChartTooltip,
    Legend,
    Filler
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    ChartTooltip,
    Legend,
    Filler
);

// Available metrics
const AVAILABLE_METRICS = [
    { id: 'cagr', label: 'CAGR (%)', field: 'local_cagr' },
    { id: 'irr', label: 'IRR (%)', field: 'local_irr' },
    { id: 'total_return', label: 'Total Return (%)', field: 'local_total_return' },
    { id: 'dividend_yield', label: 'Dividend Yield', field: 'local_dividend_yield' },
    { id: 'fee_ratio', label: 'Fee Ratio (%)', field: 'local_fee_ratio_annualized' },
    { id: 'tax_ratio', label: 'Tax Ratio (%)', field: 'local_tax_ratio_annualized' },
    { id: 'cost_ratio', label: 'Cost Ratio (%)', field: 'local_cost_ratio_annualized' },
    { id: 'total_contributions', label: 'Total Contributions', field: 'local_total_contributions' },
    { id: 'total_fees', label: 'Total Fees', field: 'local_total_fees' },
    { id: 'total_tax', label: 'Total Tax', field: 'local_total_tax' },
    { id: 'total_dividends', label: 'Total Dividends', field: 'local_total_dividends' },
    // Inflation-adjusted versions
    { id: 'cagr_real', label: 'CAGR Real (%)', field: 'local_real_cagr' },
    { id: 'irr_real', label: 'IRR Real (%)', field: 'local_real_irr' },
    { id: 'total_return_real', label: 'Total Return Real (%)', field: 'local_real_total_return' }
];

interface MetricSeries {
    id: string;
    investmentId: string | 'portfolio';
    investmentName: string;
    metricId: string;
    color: string;
}

interface GraphConfig {
    id: string;
    title: string;
    series: MetricSeries[];
    selectedMetric: string;
}

const CHART_COLORS = [
    '#007FFF', '#00C853', '#FF6B35', '#FFB700', '#9C27B0',
    '#00BCD4', '#FF5722', '#4CAF50', '#FFC107', '#E91E63'
];

export default function ViewInvestmentMetrics() {
    const [graphs, setGraphs] = useState<GraphConfig[]>([]);
    const [investments, setInvestments] = useState<any[]>([]);
    const [metricsData, setMetricsData] = useState<Map<string, any>>(new Map());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch available investments
    useEffect(() => {
        async function fetchInvestments() {
            try {
                const response = await fetch('/api/investment_names');
                const data = await response.json();

                // Add "Portfolio" option
                const investmentsList = [
                    { id: 'portfolio', name: 'Portfolio (All Investments)' },
                    ...data.investment_names.map((name: string, idx: number) => ({
                        id: `inv_${idx}`,
                        name: name
                    }))
                ];

                setInvestments(investmentsList);
                setLoading(false);
            } catch (err) {
                console.error('Error fetching investments:', err);
                setError('Failed to load investments');
                setLoading(false);
            }
        }

        fetchInvestments();
    }, []);

    // Fetch metrics data for an investment
    const fetchMetricsForInvestment = async (investmentId: string, investmentName: string) => {
        const cacheKey = investmentId;

        // Return cached data if available
        if (metricsData.has(cacheKey)) {
            return metricsData.get(cacheKey);
        }

        try {
            let url: string;

            if (investmentId === 'portfolio') {
                // Fetch portfolio-wide metrics
                url = '/api/investment_metrics/Investments?filter=portfolio';
            } else {
                // Fetch individual investment metrics
                // For now, we'll use portfolio endpoint and filter on frontend
                // TODO: Add individual investment endpoint to backend
                url = '/api/investment_metrics/Investments?filter=portfolio';
            }

            const response = await fetch(url);
            const data = await response.json();

            // Cache the data
            const newMetricsData = new Map(metricsData);
            newMetricsData.set(cacheKey, data);
            setMetricsData(newMetricsData);

            return data;
        } catch (err) {
            console.error(`Error fetching metrics for ${investmentName}:`, err);
            return null;
        }
    };

    // Add a new blank graph
    const addGraph = () => {
        const newGraph: GraphConfig = {
            id: `graph_${Date.now()}`,
            title: `Metric Chart ${graphs.length + 1}`,
            series: [],
            selectedMetric: 'cagr'
        };
        setGraphs([...graphs, newGraph]);
    };

    // Remove a graph
    const removeGraph = (graphId: string) => {
        setGraphs(graphs.filter(g => g.id !== graphId));
    };

    // Add investment series to a graph
    const addSeriesToGraph = async (graphId: string, investmentId: string) => {
        const graph = graphs.find(g => g.id === graphId);
        if (!graph) return;

        const investment = investments.find(inv => inv.id === investmentId);
        if (!investment) return;

        // Check if this investment is already in the graph
        if (graph.series.find(s => s.investmentId === investmentId)) {
            alert('This investment is already added to this graph');
            return;
        }

        // Assign a color
        const colorIndex = graph.series.length % CHART_COLORS.length;
        const color = CHART_COLORS[colorIndex];

        const newSeries: MetricSeries = {
            id: `series_${Date.now()}`,
            investmentId: investmentId,
            investmentName: investment.name,
            metricId: graph.selectedMetric,
            color: color
        };

        // Fetch data for this investment
        await fetchMetricsForInvestment(investmentId, investment.name);

        // Update graph
        const updatedGraphs = graphs.map(g => {
            if (g.id === graphId) {
                return {
                    ...g,
                    series: [...g.series, newSeries]
                };
            }
            return g;
        });

        setGraphs(updatedGraphs);
    };

    // Remove series from graph
    const removeSeriesFromGraph = (graphId: string, seriesId: string) => {
        const updatedGraphs = graphs.map(g => {
            if (g.id === graphId) {
                return {
                    ...g,
                    series: g.series.filter(s => s.id !== seriesId)
                };
            }
            return g;
        });
        setGraphs(updatedGraphs);
    };

    // Change metric for a graph
    const changeGraphMetric = async (graphId: string, metricId: string) => {
        const updatedGraphs = graphs.map(g => {
            if (g.id === graphId) {
                return {
                    ...g,
                    selectedMetric: metricId,
                    series: g.series.map(s => ({
                        ...s,
                        metricId: metricId
                    }))
                };
            }
            return g;
        });
        setGraphs(updatedGraphs);
    };

    // Prepare chart data for a graph
    const prepareChartData = (graph: GraphConfig) => {
        const metric = AVAILABLE_METRICS.find(m => m.id === graph.selectedMetric);
        if (!metric) return null;

        const datasets = graph.series.map(series => {
            const data = metricsData.get(series.investmentId);
            if (!data || !data.cagr_trend) return null;

            // Map the data based on selected metric
            let values: number[] = [];
            let labels: string[] = [];

            if (graph.selectedMetric === 'cagr') {
                values = data.cagr_trend.map((d: any) => d.value);
                labels = data.cagr_trend.map((d: any) => d.period);
            } else if (graph.selectedMetric === 'irr') {
                values = data.irr_trend.map((d: any) => d.value);
                labels = data.irr_trend.map((d: any) => d.period);
            } else if (graph.selectedMetric === 'dividend_yield') {
                values = data.dividend_yield.map((d: any) => d.value * 100);
                labels = data.dividend_yield.map((d: any) => d.period);
            } else if (graph.selectedMetric.includes('fee')) {
                values = data.fee_analysis?.map((d: any) => d.fee_ratio) || [];
                labels = data.fee_analysis?.map((d: any) => d.period) || [];
            } else if (graph.selectedMetric.includes('tax')) {
                values = data.tax_analysis?.map((d: any) => d.tax_ratio) || [];
                labels = data.tax_analysis?.map((d: any) => d.period) || [];
            } else {
                // Default to CAGR
                values = data.cagr_trend.map((d: any) => d.value);
                labels = data.cagr_trend.map((d: any) => d.period);
            }

            return {
                label: series.investmentName,
                data: values,
                borderColor: series.color,
                backgroundColor: `${series.color}20`,
                borderWidth: 2,
                tension: 0.4,
                fill: false,
                labels: labels
            };
        }).filter((dataset): dataset is NonNullable<typeof dataset> => dataset !== null);

        if (datasets.length === 0) return null;

        // Use labels from first dataset
        const labels = datasets[0]?.labels || [];

        return {
            labels: labels,
            datasets: datasets.map(({ labels: _, ...rest }) => rest)
        };
    };

    if (loading) {
        return (
            <Container maxWidth="xl" sx={{ mt: 4 }}>
                <Typography>Loading investments...</Typography>
            </Container>
        );
    }

    return (
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
            {/* Header */}
            <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h4" gutterBottom>
                        <ShowChartIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                        Investment Metrics Dashboard
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Add custom metric charts to analyze your investments over time
                    </Typography>
                </Box>
            </Box>

            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
            )}

            {/* Graphs */}
            <Grid container spacing={3}>
                {graphs.map((graph) => (
                    <Grid size={{ xs: 12 }} key={graph.id}>
                        <Card elevation={3}>
                            <CardContent>
                                {/* Graph Header */}
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h6">
                                        {AVAILABLE_METRICS.find(m => m.id === graph.selectedMetric)?.label || 'Metric Chart'}
                                    </Typography>
                                    <IconButton
                                        size="small"
                                        onClick={() => removeGraph(graph.id)}
                                        color="error"
                                    >
                                        <DeleteIcon />
                                    </IconButton>
                                </Box>

                                {/* Metric Selector */}
                                <FormControl fullWidth sx={{ mb: 3 }}>
                                    <InputLabel>Metric</InputLabel>
                                    <Select
                                        value={graph.selectedMetric}
                                        label="Metric"
                                        onChange={(e) => changeGraphMetric(graph.id, e.target.value)}
                                    >
                                        {AVAILABLE_METRICS.map(metric => (
                                            <MenuItem key={metric.id} value={metric.id}>
                                                {metric.label}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>

                                {/* Investment Selector */}
                                <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
                                    <FormControl sx={{ minWidth: 300 }}>
                                        <InputLabel>Add Investment</InputLabel>
                                        <Select
                                            label="Add Investment"
                                            value=""
                                            onChange={(e) => addSeriesToGraph(graph.id, e.target.value)}
                                        >
                                            {investments.map(inv => (
                                                <MenuItem key={inv.id} value={inv.id}>
                                                    {inv.name}
                                                </MenuItem>
                                            ))}
                                        </Select>
                                    </FormControl>

                                    {/* Active Series Chips */}
                                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                        {graph.series.map(series => (
                                            <Chip
                                                key={series.id}
                                                label={series.investmentName}
                                                onDelete={() => removeSeriesFromGraph(graph.id, series.id)}
                                                sx={{
                                                    borderLeft: `4px solid ${series.color}`,
                                                    fontWeight: 'medium'
                                                }}
                                            />
                                        ))}
                                    </Box>
                                </Box>

                                {/* Chart */}
                                {graph.series.length > 0 ? (
                                    <Box sx={{ height: 400 }}>
                                        <Line
                                            data={prepareChartData(graph) || { labels: [], datasets: [] }}
                                            options={{
                                                responsive: true,
                                                maintainAspectRatio: false,
                                                plugins: {
                                                    legend: {
                                                        position: 'top' as const,
                                                    },
                                                    title: {
                                                        display: false
                                                    },
                                                },
                                                scales: {
                                                    y: {
                                                        beginAtZero: false,
                                                        ticks: {
                                                            callback: function (value) {
                                                                if (graph.selectedMetric.includes('ratio') ||
                                                                    graph.selectedMetric.includes('yield') ||
                                                                    graph.selectedMetric === 'cagr' ||
                                                                    graph.selectedMetric === 'irr' ||
                                                                    graph.selectedMetric.includes('return')) {
                                                                    return value + '%';
                                                                }
                                                                return value.toLocaleString();
                                                            }
                                                        }
                                                    },
                                                    x: {
                                                        ticks: {
                                                            maxRotation: 45,
                                                            minRotation: 45
                                                        }
                                                    }
                                                }
                                            }}
                                        />
                                    </Box>
                                ) : (
                                    <Box
                                        sx={{
                                            height: 300,
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            border: '2px dashed #ccc',
                                            borderRadius: 2,
                                            color: 'text.secondary'
                                        }}
                                    >
                                        <Typography>
                                            Select a metric and add investments to display the chart
                                        </Typography>
                                    </Box>
                                )}
                            </CardContent>
                        </Card>
                    </Grid>
                ))}

                {/* Empty State */}
                {graphs.length === 0 && (
                    <Grid size={{ xs: 12 }}>
                        <Paper
                            sx={{
                                p: 6,
                                textAlign: 'center',
                                backgroundColor: 'background.default'
                            }}
                        >
                            <ShowChartIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
                            <Typography variant="h6" gutterBottom>
                                No Charts Yet
                            </Typography>
                            <Typography color="text.secondary" sx={{ mb: 3 }}>
                                Click the + button below to add your first metric chart
                            </Typography>
                        </Paper>
                    </Grid>
                )}
            </Grid>

            {/* Floating Add Button */}
            <Tooltip title="Add New Chart" placement="left">
                <Fab
                    color="primary"
                    aria-label="add"
                    onClick={addGraph}
                    sx={{
                        position: 'fixed',
                        bottom: 32,
                        right: 32,
                    }}
                >
                    <AddIcon />
                </Fab>
            </Tooltip>
        </Container>
    );
}
