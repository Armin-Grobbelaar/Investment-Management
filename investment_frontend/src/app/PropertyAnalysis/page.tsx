'use client';

import React, { useState, useEffect } from 'react';
import {
    Container, Paper, Button, IconButton, Box, Typography, Grid, Card, CardContent,
    TextField, CircularProgress, Accordion, AccordionSummary, AccordionDetails, Table, TableBody, TableCell, TableHead, TableRow, TableContainer,
    FormControlLabel, Checkbox
} from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import HomeWorkIcon from '@mui/icons-material/HomeWork';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';
import KeyboardBackspaceIcon from '@mui/icons-material/KeyboardBackspace';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { Line } from 'react-chartjs-2';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DownloadIcon from '@mui/icons-material/Download';

const DB_NAME = process.env.NEXT_PUBLIC_DB_NAME || 'Investments';

export default function PropertyAnalysis() {
    const router = useRouter();
    const [darkMode, setDarkMode] = useState(true);
    const [loading, setLoading] = useState(false);
    const [scraping, setScraping] = useState(false);
    const [scrapeMsg, setScrapeMsg] = useState('');
    const [propertyUrl, setPropertyUrl] = useState('');
    const [result, setResult] = useState<any>(null);
    const [sensitivity, setSensitivity] = useState<any>(null);
    const [monteCarlo, setMonteCarlo] = useState<any>(null);
    const [downloadingPdf, setDownloadingPdf] = useState(false);
    const [configLoaded, setConfigLoaded] = useState(false);

    const theme = darkMode ? brandingDarkTheme : brandingLightTheme;

    const [inputs, setInputs] = useState({
        property_name: "Test Property",
        purchase_price: 1500000,
        deposit_amount: 150000,
        bond_interest_rate: 11.75,
        bond_term_years: 20,
        transfer_costs: 30000,
        bond_registration_costs: 25000,
        other_acquisition_costs: 5000,
        monthly_levy: 1500,
        monthly_rates: 800,
        monthly_insurance: 400,
        monthly_maintenance_reserve: 500,
        monthly_management_fee_pct: 8,
        monthly_other_costs: 0,
        monthly_rental_income: 12000,
        // Growth/inflation rates are percentages on the backend (e.g. 7.0 = 7%).
        // Earlier defaults (0.04/0.05) were fraction-scale and produced
        // ~0.05% growth instead of 5%.
        rental_growth_rate_pa: 5.0,
        vacancy_rate_pct: 5,
        property_growth_rate_pa: 7.0,
        inflation_rate: 5.0,
        projection_years: 20,
        cgt_inclusion_rate: 0.40,
        cgt_marginal_tax_rate: 0.45,
        is_primary_residence: false
    });

    // Fetch configurable default rates from the backend configuration table
    // so property analysis uses the same values as the backend calculators.
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const res = await axios.get(`/api/config/${DB_NAME}`);
                const cfg: Record<string, string> = res.data?.settings || res.data || {};
                const num = (key: string, fallback: number) => {
                    const v = cfg[key];
                    if (v === undefined || v === null || v === '') return fallback;
                    const n = Number(v);
                    return Number.isFinite(n) ? n : fallback;
                };
                if (!cancelled) {
                    setInputs(prev => ({
                        ...prev,
                        bond_interest_rate: num('default_bond_interest_rate', prev.bond_interest_rate),
                        rental_growth_rate_pa: num('default_rental_growth_rate', prev.rental_growth_rate_pa),
                        vacancy_rate_pct: num('default_vacancy_rate', prev.vacancy_rate_pct),
                        property_growth_rate_pa: num('default_property_growth_rate', prev.property_growth_rate_pa),
                        inflation_rate: num('default_inflation_rate', prev.inflation_rate),
                        projection_years: num('default_projection_years', prev.projection_years),
                        cgt_inclusion_rate: num('cgt_inclusion_rate', prev.cgt_inclusion_rate),
                        cgt_marginal_tax_rate: num('cgt_marginal_tax_rate', prev.cgt_marginal_tax_rate),
                    }));
                    setConfigLoaded(true);
                }
            } catch (err) {
                console.error('Failed to load config defaults:', err);
            }
        })();
        return () => { cancelled = true; };
    }, []);

    const handleChange = (e: any) => {
        const { name, value } = e.target;
        setInputs(prev => ({
            ...prev,
            [name]: name === 'property_name' ? value : Number(value)
        }));
    };

    const handlePrimaryResidenceChange = (e: any) => {
        const { checked } = e.target;
        setInputs(prev => ({ ...prev, is_primary_residence: checked }));
    };

    const handleScrapeUrl = async () => {
        if (!propertyUrl.trim()) {
            setScrapeMsg('Please enter a property listing URL first.');
            return;
        }
        setScraping(true);
        setScrapeMsg('');
        try {
            const res = await axios.post('/api/property/scrape', { url: propertyUrl.trim() });
            const data = res.data;
            if (!data || (!data.purchase_price && !data.monthly_rental_income && !data.property_name)) {
                setScrapeMsg('Could not extract values from that URL. Please fill in the fields manually.');
            } else {
                const updates: any = {};
                if (data.property_name) updates.property_name = String(data.property_name).slice(0, 100);
                if (data.purchase_price && data.purchase_price > 0) updates.purchase_price = Number(data.purchase_price);
                if (data.monthly_rental_income && data.monthly_rental_income > 0) updates.monthly_rental_income = Number(data.monthly_rental_income);
                setInputs(prev => ({ ...prev, ...updates }));
                const missing: string[] = [];
                if (!updates.purchase_price) missing.push('purchase price');
                if (!updates.monthly_rental_income) missing.push('monthly rent');
                setScrapeMsg(
                    (updates.property_name ? `Found "${updates.property_name}". ` : '') +
                    (missing.length
                        ? `Could not extract ${missing.join(' and ')} — please enter these values manually.`
                        : 'Extracted values from the listing. Review and adjust if needed.')
                );
            }
        } catch (err) {
            console.error(err);
            setScrapeMsg('Scraping failed. Please fill in the fields manually.');
        }
        setScraping(false);
    };

    const handleCalculate = async () => {
        setLoading(true);
        try {
            const res = await axios.post('/api/property/calculate', inputs);
            setResult(res.data);
            
            const mcRes = await axios.post('/api/property/monte_carlo', inputs);
            setMonteCarlo(mcRes.data);
            
            const sensRes = await axios.post('/api/property/sensitivity', inputs);
            setSensitivity(sensRes.data);
        } catch (err) {
            console.error(err);
            alert("Error calculating property analysis");
        }
        setLoading(false);
    };

    const handleDownloadPdf = async () => {
        if (!result) return;
        setDownloadingPdf(true);
        try {
            const payload = {
                inputs,
                result,
                monte_carlo: monteCarlo,
                sensitivity
            };
            const res = await axios.post('/api/property/report', payload, { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${inputs.property_name || 'property'}_report.pdf`);
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error(err);
            alert("Error generating PDF report");
        }
        setDownloadingPdf(false);
    };

    const formatCurr = (v: number) => `R ${new Intl.NumberFormat('en-ZA').format(v || 0)}`;
    const formatPct = (v: number) => `${(v || 0).toFixed(2)}%`;

    return (
        <ThemeProvider theme={theme}>
            <Box sx={{ backgroundColor: 'background.default', minHeight: '100vh', pb: 6, pt: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 3, mb: 4, alignItems: 'center' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <DrawerComponent />
                        <IconButton onClick={() => router.back()} color="inherit" size="large">
                            <KeyboardBackspaceIcon />
                        </IconButton>
                        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                            <HomeWorkIcon sx={{ mr: 1, verticalAlign: 'middle', fontSize: 36, color: 'primary.main' }} />
                            Property Analysis
                        </Typography>
                    </Box>
                    <IconButton onClick={() => setDarkMode(!darkMode)} color="inherit">
                        {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
                    </IconButton>
                </Box>

                <Container maxWidth="xl">
                    <Grid container spacing={3}>
                        <Grid size={{xs: 12, md: 4}}>
                            <Paper sx={{ p: 3, borderRadius: 2 }}>
                                <Typography variant="h6" gutterBottom>Property Parameters</Typography>
                                <Grid container spacing={2}>
                                    <Grid size={12}>
                                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                            Paste a property listing URL (e.g. Private Property, Property24) and we will try to extract the purchase price and rental income automatically.
                                        </Typography>
                                    </Grid>
                                    <Grid size={9}>
                                        <TextField
                                            fullWidth
                                            label="Property Listing URL"
                                            value={propertyUrl}
                                            onChange={e => setPropertyUrl(e.target.value)}
                                            placeholder="https://www.privateproperty.co.za/..."
                                            size="small"
                                        />
                                    </Grid>
                                    <Grid size={3}>
                                        <Button
                                            fullWidth
                                            variant="outlined"
                                            onClick={handleScrapeUrl}
                                            disabled={scraping}
                                            sx={{ height: '100%' }}
                                        >
                                            {scraping ? <CircularProgress size={20} /> : 'Scrape URL'}
                                        </Button>
                                    </Grid>
                                    {scrapeMsg && (
                                        <Grid size={12}>
                                            <Typography
                                                variant="body2"
                                                sx={{
                                                    color: scrapeMsg.includes('Could not') || scrapeMsg.includes('failed') ? 'warning.main' : 'success.main',
                                                    bgcolor: 'background.default',
                                                    borderRadius: 1,
                                                    p: 1,
                                                }}
                                            >
                                                {scrapeMsg}
                                            </Typography>
                                        </Grid>
                                    )}
                                    <Grid size={12}><TextField fullWidth label="Property Name" name="property_name" value={inputs.property_name} onChange={handleChange} /></Grid>
                                    <Grid size={6}><TextField fullWidth label="Purchase Price" name="purchase_price" type="number" value={inputs.purchase_price} onChange={handleChange} /></Grid>
                                    <Grid size={6}><TextField fullWidth label="Deposit" name="deposit_amount" type="number" value={inputs.deposit_amount} onChange={handleChange} /></Grid>
                                    <Grid size={6}><TextField fullWidth label="Interest Rate (%)" name="bond_interest_rate" type="number" value={inputs.bond_interest_rate} onChange={handleChange} /></Grid>
                                    <Grid size={6}><TextField fullWidth label="Term (Years)" name="bond_term_years" type="number" value={inputs.bond_term_years} onChange={handleChange} /></Grid>
                                    <Grid size={6}><TextField fullWidth label="Monthly Rent" name="monthly_rental_income" type="number" value={inputs.monthly_rental_income} onChange={handleChange} /></Grid>
                                    <Grid size={6}><TextField fullWidth label="Levies" name="monthly_levy" type="number" value={inputs.monthly_levy} onChange={handleChange} /></Grid>
                                    <Grid size={6}><TextField fullWidth label="Rates" name="monthly_rates" type="number" value={inputs.monthly_rates} onChange={handleChange} /></Grid>
                                    <Grid size={6}><TextField fullWidth label="Maintenance/m" name="monthly_maintenance_reserve" type="number" value={inputs.monthly_maintenance_reserve} onChange={handleChange} /></Grid>
                                    <Grid size={12}>
                                        <FormControlLabel
                                            control={<Checkbox checked={inputs.is_primary_residence} onChange={handlePrimaryResidenceChange} />}
                                            label="This property is my primary residence (applies the R2m CGT exclusion on sale)"
                                        />
                                    </Grid>
                                    <Grid size={12}>
                                        <Button variant="contained" fullWidth size="large" onClick={handleCalculate} disabled={loading}>
                                            {loading ? <CircularProgress size={24} /> : "Calculate Analysis"}
                                        </Button>
                                    </Grid>
                                    {result && (
                                        <Grid size={12}>
                                            <Button 
                                                variant="outlined" 
                                                fullWidth 
                                                size="large" 
                                                onClick={handleDownloadPdf}
                                                disabled={downloadingPdf}
                                                startIcon={downloadingPdf ? <CircularProgress size={20} /> : <PictureAsPdfIcon />}
                                            >
                                                {downloadingPdf ? "Generating PDF..." : "Download PDF Report"}
                                            </Button>
                                        </Grid>
                                    )}
                                </Grid>
                            </Paper>
                        </Grid>
                        
                        <Grid size={{xs: 12, md: 8}}>
                            {result && (
                                <Box>
                                    <Grid container spacing={2} sx={{ mb: 3 }}>
                                        <Grid size={4}>
                                            <Card><CardContent>
                                                <Typography color="text.secondary">Total Acquisition Cost</Typography>
                                                <Typography variant="h5">{formatCurr(result.total_acquisition_cost)}</Typography>
                                            </CardContent></Card>
                                        </Grid>
                                        <Grid size={4}>
                                            <Card><CardContent>
                                                <Typography color="text.secondary">10yr IRR (Nominal / Real)</Typography>
                                                <Typography variant="h5" color="primary">{formatPct(result.irr_10yr)} / {formatPct(result.real_irr_10yr)}</Typography>
                                            </CardContent></Card>
                                        </Grid>
                                        <Grid size={4}>
                                            <Card><CardContent>
                                                <Typography color="text.secondary">First Year Net Yield</Typography>
                                                <Typography variant="h5">{formatPct(result.first_year_net_yield)}</Typography>
                                            </CardContent></Card>
                                        </Grid>
                                        <Grid size={4}>
                                            <Card><CardContent>
                                                <Typography color="text.secondary">Transfer Duty</Typography>
                                                <Typography variant="h5" color="error">{formatCurr(result.transfer_duty)}</Typography>
                                            </CardContent></Card>
                                        </Grid>
                                        <Grid size={4}>
                                            <Card><CardContent>
                                                <Typography color="text.secondary">CGT at year 10</Typography>
                                                <Typography variant="h5" color="error">{formatCurr(result.cgt_10yr)}</Typography>
                                            </CardContent></Card>
                                        </Grid>
                                        <Grid size={4}>
                                            <Card><CardContent>
                                                <Typography color="text.secondary">Monte Carlo p50 IRR</Typography>
                                                <Typography variant="h5">{monteCarlo ? formatPct(monteCarlo.percentiles_irr.p50) : '-'}</Typography>
                                            </CardContent></Card>
                                        </Grid>
                                    </Grid>

                                    <Paper sx={{ p: 3, borderRadius: 2, mb: 3, height: 400 }}>
                                        <Typography variant="h6" gutterBottom>Annual Cash Flow & Cumulative</Typography>
                                        <Line data={{
                                            labels: result.annual_cash_flows.map((_: any, i: number) => `Year ${i}`),
                                            datasets: [
                                                { label: "Annual Cash Flow", data: result.annual_cash_flows, borderColor: "#4caf50", backgroundColor: "#4caf5033", fill: true },
                                                { label: "Cumulative", data: result.projection.map((p:any) => p.cumulative_cash_flow), borderColor: "#2196f3", backgroundColor: "transparent" }
                                            ]
                                        }} options={{ maintainAspectRatio: false }} />
                                    </Paper>
                                </Box>
                            )}
                        </Grid>
                    </Grid>
                </Container>
            </Box>
        </ThemeProvider>
    );
}
