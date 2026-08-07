"use client";
import React, { useEffect, useState } from 'react';
import {
  Container, Paper, Grid, Typography, Box, FormControl, InputLabel,
  Select, MenuItem, Button, IconButton, Dialog, DialogActions,
  DialogContent, DialogTitle, Snackbar, Alert, Autocomplete, TextField,
  CircularProgress, Card, CardContent, CardActions, Divider, Chip
} from "@mui/material";
import axios from 'axios';
import { useRouter } from 'next/navigation';
import KeyboardBackspaceIcon from '@mui/icons-material/KeyboardBackspace';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import DownloadIcon from '@mui/icons-material/Download';
import VisibilityIcon from '@mui/icons-material/Visibility';
import RefreshIcon from '@mui/icons-material/Refresh';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';

interface Investment {
  id: number;
  investment_name: string;
  institution_name: string;
  factsheet_count: number;
  latest_factsheet_date: string;
}

interface Factsheet {
  id: number;
  factsheet_date: string;
  factsheet_type: string;
  factsheet_year: number;
  factsheet_month: number;
  file_name: string;
  file_size_bytes: number;
  downloaded_at: string;
}

export default function FactsheetsPage() {
  const router = useRouter();
  const [darkMode, setDarkMode] = useState(true);
  const [investments, setInvestments] = useState<Investment[]>([]);
  const [selectedInvestment, setSelectedInvestment] = useState<Investment | null>(null);
  const [factsheets, setFactsheets] = useState<Factsheet[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingFactsheets, setLoadingFactsheets] = useState(false);
  const [downloadingLatest, setDownloadingLatest] = useState(false);
  const [downloadingAll, setDownloadingAll] = useState(false);
  
  const [viewPdf, setViewPdf] = useState<{ url: string, title: string } | null>(null);
  const [snack, setSnack] = useState<{ open: boolean, message: string, severity: 'success' | 'error' | 'info' }>({ open: false, message: '', severity: 'info' });

  // Filter states
  const [selectedYear, setSelectedYear] = useState<string>('All');
  const [selectedMonth, setSelectedMonth] = useState<string>('All');

  const currentYear = new Date().getFullYear();
  const years = ['All', ...Array.from({length: 10}, (_, i) => (currentYear - i).toString())];
  const months = ['All', ...Array.from({length: 12}, (_, i) => (i + 1).toString())];

  useEffect(() => {
    fetchInvestments();
  }, []);

  useEffect(() => {
    if (selectedInvestment) {
      fetchFactsheets();
    } else {
      setFactsheets([]);
    }
  }, [selectedInvestment, selectedYear, selectedMonth]);

  const fetchInvestments = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/factsheets/Investments/list');
      setInvestments(res.data);
    } catch (error: any) {
      showSnack('Failed to load investments', 'error');
    }
    setLoading(false);
  };

  const fetchFactsheets = async () => {
    if (!selectedInvestment) return;
    setLoadingFactsheets(true);
    try {
      let url = `/api/factsheets/Investments/${selectedInvestment.id}`;
      const params = new URLSearchParams();
      if (selectedYear !== 'All') params.append('year', selectedYear);
      if (selectedMonth !== 'All') params.append('month', selectedMonth);
      if (params.toString()) url += `?${params.toString()}`;
      
      const res = await axios.get(url);
      setFactsheets(res.data);
    } catch (error: any) {
      showSnack('Failed to load factsheets', 'error');
    }
    setLoadingFactsheets(false);
  };

  const handleDownloadLatest = async () => {
    if (!selectedInvestment) return;
    setDownloadingLatest(true);
    try {
      const res = await axios.post(`/api/factsheets/Investments/download/${selectedInvestment.id}`);
      if (res.data.details?.success) {
        showSnack(`Successfully downloaded latest factsheet for ${selectedInvestment.investment_name}`, 'success');
        fetchFactsheets(); // Refresh the list
      } else {
        showSnack(`Failed: ${res.data.details?.error || 'Unknown error'}`, 'error');
      }
    } catch (error: any) {
      showSnack('Failed to trigger download', 'error');
    }
    setDownloadingLatest(false);
  };

  const handleDownloadAll = async () => {
    setDownloadingAll(true);
    try {
      await axios.post('/api/factsheets/Investments/download_all');
      showSnack('Bulk download triggered in background', 'success');
    } catch (error: any) {
      showSnack('Failed to trigger bulk download', 'error');
    }
    setDownloadingAll(false);
  };

  const showSnack = (message: string, severity: 'success' | 'error' | 'info') => {
    setSnack({ open: true, message, severity });
  };

  const toggleDarkMode = () => setDarkMode(prev => !prev);
  const theme = darkMode ? brandingDarkTheme : brandingLightTheme;

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Mock menu items since we don't fetch dashboard data here
  const menuItems = [
    {
      "heading": "Tools & Analysis",
      "items": ["Dashboard", "Edit Data", "Factsheets", "Property Analysis", "View Metrics", "Monte Carlo"],
      "urls": ["/Investments", "/EditInvestmentData", "/Factsheets", "/PropertyAnalysis", "/ViewInvestmentMetrics", "/ViewInvestmentPredictions"]
    }
  ];

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ backgroundColor: 'background.default', minHeight: '100vh', pt: 2, pb: 6 }}>
        {/* Navigation & Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 3, mb: 4, alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <DrawerComponent menuItems={menuItems} />
            <IconButton onClick={() => router.back()} color="inherit" size="large">
              <KeyboardBackspaceIcon />
            </IconButton>
            <Typography variant="h4" sx={{ fontWeight: 'bold', background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Factsheets & MDDs
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
             <Button 
                variant="outlined" 
                color="primary" 
                startIcon={<RefreshIcon />}
                onClick={handleDownloadAll}
                disabled={downloadingAll}
              >
                {downloadingAll ? 'Triggering...' : 'Sync All Factsheets'}
              </Button>
            <IconButton onClick={toggleDarkMode} color="inherit">
              {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Box>
        </Box>

        <Container maxWidth="xl">
          <Grid container spacing={3}>
            {/* Left Panel: Selectors */}
            <Grid size={{xs: 12, md: 4, lg: 3}}>
              <Paper elevation={3} sx={{ p: 3, borderRadius: 3, height: '100%', background: theme.palette.background.paper, backdropFilter: 'blur(10px)' }}>
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  Select Investment
                </Typography>
                
                {loading ? (
                  <Box display="flex" justifyContent="center" py={3}>
                    <CircularProgress />
                  </Box>
                ) : (
                  <Autocomplete
                    options={investments}
                    getOptionLabel={(option) => `${option.institution_name} - ${option.investment_name}`}
                    value={selectedInvestment}
                    onChange={(_, newValue) => setSelectedInvestment(newValue)}
                    renderInput={(params) => <TextField {...params} label="Search Investment" variant="outlined" margin="normal" />}
                    renderOption={(props, option) => (
                      <li {...props}>
                        <Box>
                          <Typography variant="body1">{option.investment_name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {option.institution_name} • {option.factsheet_count} factsheets
                          </Typography>
                        </Box>
                      </li>
                    )}
                  />
                )}
                
                <Divider sx={{ my: 3 }} />
                
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  Filters
                </Typography>
                
                <FormControl fullWidth margin="normal">
                  <InputLabel>Year</InputLabel>
                  <Select
                    value={selectedYear}
                    label="Year"
                    onChange={(e) => setSelectedYear(e.target.value)}
                  >
                    {years.map(y => <MenuItem key={y} value={y}>{y}</MenuItem>)}
                  </Select>
                </FormControl>

                <FormControl fullWidth margin="normal">
                  <InputLabel>Month</InputLabel>
                  <Select
                    value={selectedMonth}
                    label="Month"
                    onChange={(e) => setSelectedMonth(e.target.value)}
                  >
                    {months.map(m => <MenuItem key={m} value={m}>{m}</MenuItem>)}
                  </Select>
                </FormControl>

                {selectedInvestment && (
                  <Box mt={4}>
                    <Button 
                      variant="contained" 
                      color="primary" 
                      fullWidth 
                      startIcon={downloadingLatest ? <CircularProgress size={20} color="inherit" /> : <DownloadIcon />}
                      onClick={handleDownloadLatest}
                      disabled={downloadingLatest}
                      sx={{ py: 1.5, borderRadius: 2 }}
                    >
                      Fetch Latest MDD
                    </Button>
                  </Box>
                )}
              </Paper>
            </Grid>

            {/* Right Panel: Results */}
            <Grid size={{xs: 12, md: 8, lg: 9}}>
              {!selectedInvestment ? (
                <Paper elevation={0} sx={{ p: 5, borderRadius: 3, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'transparent', border: '1px dashed grey' }}>
                  <Typography variant="h6" color="text.secondary">
                    Select an investment to view its factsheets.
                  </Typography>
                </Paper>
              ) : (
                <Paper elevation={3} sx={{ p: 3, borderRadius: 3, minHeight: '600px' }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                    <Typography variant="h5" fontWeight="bold">
                      {selectedInvestment.investment_name}
                    </Typography>
                    <Chip label={`${factsheets.length} files found`} color="primary" variant="outlined" />
                  </Box>
                  
                  {loadingFactsheets ? (
                     <Box display="flex" justifyContent="center" py={10}>
                       <CircularProgress />
                     </Box>
                  ) : factsheets.length === 0 ? (
                    <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={10}>
                       <PictureAsPdfIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2, opacity: 0.5 }} />
                       <Typography variant="h6" color="text.secondary">No factsheets found for this selection.</Typography>
                    </Box>
                  ) : (
                    <Grid container spacing={2}>
                      {factsheets.map(fs => (
                        <Grid size={{ xs: 12, sm: 6, md: 4 }} key={fs.id}>
                          <Card variant="outlined" sx={{ borderRadius: 2, '&:hover': { boxShadow: 4, borderColor: 'primary.main' }, transition: '0.2s' }}>
                            <CardContent>
                              <Box display="flex" alignItems="center" gap={1} mb={1}>
                                <PictureAsPdfIcon color="error" />
                                <Typography variant="h6" noWrap>{fs.factsheet_year} - {new Date(0, fs.factsheet_month - 1).toLocaleString('default', { month: 'long' })}</Typography>
                              </Box>
                              <Typography variant="body2" color="text.secondary" gutterBottom>
                                {fs.factsheet_type}
                              </Typography>
                              <Typography variant="caption" display="block" color="text.secondary">
                                Date: {new Date(fs.factsheet_date).toLocaleDateString()}
                              </Typography>
                              <Typography variant="caption" display="block" color="text.secondary">
                                Size: {formatBytes(fs.file_size_bytes)}
                              </Typography>
                            </CardContent>
                            <Divider />
                            <CardActions sx={{ justifyContent: 'space-between', px: 2 }}>
                              <Button 
                                size="small" 
                                startIcon={<VisibilityIcon />}
                                onClick={() => setViewPdf({ url: `/api/factsheets/Investments/${selectedInvestment.id}/${fs.factsheet_year}/${fs.factsheet_month}`, title: `${selectedInvestment.investment_name} - ${fs.factsheet_year}/${fs.factsheet_month}` })}
                              >
                                View
                              </Button>
                              <Button 
                                size="small" 
                                startIcon={<DownloadIcon />}
                                component="a"
                                href={`/api/factsheets/Investments/${selectedInvestment.id}/${fs.factsheet_year}/${fs.factsheet_month}`}
                                download={fs.file_name}
                              >
                                Download
                              </Button>
                            </CardActions>
                          </Card>
                        </Grid>
                      ))}
                    </Grid>
                  )}
                </Paper>
              )}
            </Grid>
          </Grid>
        </Container>

        {/* PDF Viewer Dialog */}
        <Dialog 
          open={!!viewPdf} 
          onClose={() => setViewPdf(null)}
          maxWidth="lg"
          fullWidth
          PaperProps={{ sx: { height: '90vh', borderRadius: 3 } }}
        >
          <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pb: 1 }}>
            <Typography variant="h6" fontWeight="bold">{viewPdf?.title}</Typography>
            <Button onClick={() => setViewPdf(null)} color="inherit">Close</Button>
          </DialogTitle>
          <Divider />
          <DialogContent sx={{ p: 0, overflow: 'hidden' }}>
            {viewPdf && (
              <iframe 
                src={viewPdf.url} 
                width="100%" 
                height="100%" 
                style={{ border: 'none' }}
                title="PDF Viewer"
              />
            )}
          </DialogContent>
        </Dialog>

        {/* Snackbar for notifications */}
        <Snackbar
          open={snack.open}
          autoHideDuration={6000}
          onClose={() => setSnack(prev => ({ ...prev, open: false }))}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert onClose={() => setSnack(prev => ({ ...prev, open: false }))} severity={snack.severity} sx={{ width: '100%' }}>
            {snack.message}
          </Alert>
        </Snackbar>
      </Box>
    </ThemeProvider>
  );
}
