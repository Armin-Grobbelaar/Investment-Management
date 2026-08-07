"use client";
import { Button, Container, FormControl, FormHelperText, Grid, InputLabel, IconButton, MenuItem, Select, TextField, ThemeProvider, Typography, useTheme, Box } from '@mui/material'
import React from 'react'
import dayjs from 'dayjs';
import { useState } from 'react';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme'
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { Form, useFormik } from 'formik';
import { addInvestmentSchema } from '../Schemas/YupSchema';
import DialogComponent from '../Reusable Components/Dialog Pop Up/dialogpopup';

const onSubmit = () => {
  console.log("Submitted")
};

export default function AddInvestment() {
  const [darkMode, setDarkMode] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [dialogValues, setDialogValues] = useState<(string | number)[]>([]);
  const theme = useTheme();
  const [apiMessage, setApiMessage] = useState<string | null>(null);
  

  const {
    values,
    errors,
    touched,
    handleBlur,
    handleChange,
    handleSubmit,
    resetForm,
  } = useFormik({
    initialValues: {
      databaseName: "Investments",
      institutionsName: "",
      initialInvestmentDate: dayjs(),
      investmentType: "",
      investmentName: "",
      investmentTicker: "",
      unitCurrency: "",
      initialUnitPrice: 0.0,
      currentUnitPrice: 0.0,
      numberOfUnitsHeld: 0.0,
      totalDividends: 0.0,
      totalTax: 0.0,
      totalFees: 0.0,
      investmentFee: 0.0,
      investmentStatus: "Active",
    },
    validationSchema: addInvestmentSchema,
    onSubmit: async (values) => {
      try {
        const response = await fetch("/api/add_investment/Investments", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            institution_name: values.institutionsName,
            initial_investment_date: values.initialInvestmentDate.format("YYYY-MM-DD"),
            investment_type: values.investmentType,
            investment_name: values.investmentName,
            investment_ticker: values.investmentTicker,
            unit_currency: values.unitCurrency,
            initial_unit_price: values.initialUnitPrice,
            unit_price: values.currentUnitPrice,
            number_of_units_held: values.numberOfUnitsHeld,
            total_dividends_received: values.totalDividends,
            total_tax_paid: values.totalTax,
            total_fees_paid: values.totalFees,
            investment_fee: values.investmentFee,
            investment_status: values.investmentStatus
          }),
        });

        const data = await response.json();

        if (response.ok) {
          setApiMessage("Investment added successfully!");
          resetForm(); // Clear the form after a successful submission
        } else {
          setApiMessage(`Error: ${data.message}`);
        }
      } catch (error) {
        setApiMessage("Failed to add investment. Please try again.");
        console.error(error);
      }
    },
  });

  const handleDialogOpen = () => {
    const mappedValues = [
      values.institutionsName,
      values.initialInvestmentDate.format("YYYY-MM-DD"),
      values.investmentType,
      values.investmentName,
      values.investmentTicker,
      values.unitCurrency,
      values.initialUnitPrice,
      values.currentUnitPrice,
      values.numberOfUnitsHeld,
      values.totalDividends,
      values.totalTax,
      values.totalFees,
      values.investmentFee,
      values.investmentStatus,
    ];
    setDialogValues(mappedValues);
    setIsDialogOpen(true);
  };
  
  const handleDialogClose = () => {
    setIsDialogOpen(false);
  };

  const toggleDarkMode = () => {
    setDarkMode(prevMode => !prevMode);
  };

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
      <div style={{
        backgroundColor: darkMode ? '#222' : '#f1f2f4',
        minHeight: '100vh',
        transition: 'background-color 0.3s',
        padding: '32px 0'
      }}>
        <Container maxWidth="lg">
          {/* Dark Mode Toggle */}
          <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
            <IconButton onClick={toggleDarkMode} color="inherit" size="large">
              {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Box>

          {/* Title */}
          <Box sx={{ mb: 4, mt: 8 }}>
            <Typography variant="h4" component="h1" gutterBottom>
              Add New Investment
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Enter the details below to add a new investment to your portfolio
            </Typography>
          </Box>

          <form onSubmit={handleSubmit}>
            <Box sx={{
              backgroundColor: theme.palette.background.paper,
              borderRadius: 2,
              p: 4,
              boxShadow: theme.palette.mode === 'dark' ? 2 : 1,
            }}>
              <Grid container spacing={3}>

                {/* Basic Information Section */}
                <Grid size={{ xs: 12 }}>
                  <Typography variant="h6" gutterBottom sx={{ mb: 2, borderBottom: `1px solid ${theme.palette.divider}`, pb: 1 }}>
                    Basic Information
                  </Typography>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    name="institutionsName"
                    label="Institution Name"
                    required
                    fullWidth
                    value={values.institutionsName}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.institutionsName && !!errors.institutionsName}
                    helperText={errors.institutionsName}
                    variant="outlined"
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    name="investmentName"
                    label="Investment Name"
                    required
                    fullWidth
                    value={values.investmentName}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.investmentName && !!errors.investmentName}
                    helperText={errors.investmentName}
                    variant="outlined"
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    name="investmentTicker"
                    label="Investment Ticker/Class"
                    required
                    fullWidth
                    value={values.investmentTicker}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.investmentTicker && !!errors.investmentTicker}
                    helperText={errors.investmentTicker}
                    variant="outlined"
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <FormControl fullWidth error={touched.investmentType && !!errors.investmentType}>
                    <InputLabel id="investment-type-label">Investment Type</InputLabel>
                    <Select
                      name="investmentType"
                      labelId="investment-type-label"
                      id="investment_type"
                      label="Investment Type"
                      required
                      value={values.investmentType}
                      onChange={handleChange}
                      onBlur={handleBlur}
                    >
                      <MenuItem value="ETF">ETF</MenuItem>
                      <MenuItem value="Unit Trust">Unit Trust</MenuItem>
                      <MenuItem value="Forex">Forex</MenuItem>
                      <MenuItem value="ETN">ETN</MenuItem>
                      <MenuItem value="Hedge Fund">Hedge Fund</MenuItem>
                      <MenuItem value="Deposit">Deposit</MenuItem>
                      <MenuItem value="RA">Retirement Annuity (RA)</MenuItem>
                      <MenuItem value="TFSA">Tax-Free Savings (TFSA)</MenuItem>
                      <MenuItem value="Share">Share / Stock</MenuItem>
                    </Select>
                    <FormHelperText>{errors.investmentType}</FormHelperText>
                  </FormControl>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <FormControl fullWidth error={touched.unitCurrency && !!errors.unitCurrency}>
                    <InputLabel id="unit-currency-label">Currency</InputLabel>
                    <Select
                      name="unitCurrency"
                      labelId="unit-currency-label"
                      id="unit_currency"
                      label="Currency"
                      required
                      value={values.unitCurrency}
                      onChange={handleChange}
                      onBlur={handleBlur}
                    >
                      <MenuItem value="ZAR">ZAR - South African Rand</MenuItem>
                      <MenuItem value="USD">USD - US Dollar</MenuItem>
                      <MenuItem value="GBP">GBP - British Pound</MenuItem>
                      <MenuItem value="EUR">EUR - Euro</MenuItem>
                    </Select>
                    <FormHelperText>{errors.unitCurrency}</FormHelperText>
                  </FormControl>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <FormControl fullWidth>
                    <LocalizationProvider dateAdapter={AdapterDayjs}>
                      <DatePicker
                        label="Initial Investment Date"
                        value={values.initialInvestmentDate}
                        onChange={(date) =>
                          handleChange({
                            target: { name: "initialInvestmentDate", value: date },
                          })
                        }
                        slotProps={{
                          textField: {
                            variant: "outlined",
                            fullWidth: true,
                            required: true,
                          },
                        }}
                      />
                    </LocalizationProvider>
                  </FormControl>
                </Grid>

                {/* Pricing Information Section */}
                <Grid size={{ xs: 12 }}>
                  <Typography variant="h6" gutterBottom sx={{ mt: 3, mb: 2, borderBottom: `1px solid ${theme.palette.divider}`, pb: 1 }}>
                    Pricing Information
                  </Typography>
                </Grid>

                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    name="initialUnitPrice"
                    label="Initial Unit Price"
                    type="number"
                    required
                    fullWidth
                    value={values.initialUnitPrice}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.initialUnitPrice && !!errors.initialUnitPrice}
                    helperText={errors.initialUnitPrice}
                    variant="outlined"
                    slotProps={{
                      htmlInput: {
                        min: "0",
                        step: "0.01"
                      }
                    }}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    name="currentUnitPrice"
                    label="Current Unit Price"
                    type="number"
                    required
                    fullWidth
                    value={values.currentUnitPrice}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.currentUnitPrice && !!errors.currentUnitPrice}
                    helperText={errors.currentUnitPrice}
                    variant="outlined"
                    slotProps={{
                      htmlInput: {
                        min: "0",
                        step: "0.01"
                      }
                    }}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    name="numberOfUnitsHeld"
                    label="Number of Units Held"
                    type="number"
                    required
                    fullWidth
                    value={values.numberOfUnitsHeld}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.numberOfUnitsHeld && !!errors.numberOfUnitsHeld}
                    helperText={errors.numberOfUnitsHeld}
                    variant="outlined"
                    slotProps={{
                      htmlInput: {
                        min: "0",
                        step: "0.01"
                      }
                    }}
                  />
                </Grid>

                {/* Financial Information Section */}
                <Grid size={{ xs: 12 }}>
                  <Typography variant="h6" gutterBottom sx={{ mt: 3, mb: 2, borderBottom: `1px solid ${theme.palette.divider}`, pb: 1 }}>
                    Financial Information
                  </Typography>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    name="totalDividends"
                    label="Total Dividends Received"
                    type="number"
                    required
                    fullWidth
                    value={values.totalDividends}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.totalDividends && !!errors.totalDividends}
                    helperText={errors.totalDividends}
                    variant="outlined"
                    slotProps={{
                      htmlInput: {
                        min: "0",
                        step: "0.01"
                      }
                    }}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    name="totalFees"
                    label="Total Fees Paid"
                    type="number"
                    required
                    fullWidth
                    value={values.totalFees}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.totalFees && !!errors.totalFees}
                    helperText={errors.totalFees}
                    variant="outlined"
                    slotProps={{
                      htmlInput: {
                        min: "0",
                        step: "0.01"
                      }
                    }}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    name="totalTax"
                    label="Total Tax Paid"
                    type="number"
                    required
                    fullWidth
                    value={values.totalTax}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.totalTax && !!errors.totalTax}
                    helperText={errors.totalTax}
                    variant="outlined"
                    slotProps={{
                      htmlInput: {
                        min: "0",
                        step: "0.01"
                      }
                    }}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    name="investmentFee"
                    label="Investment Fee (%)"
                    type="number"
                    required
                    fullWidth
                    value={values.investmentFee}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    error={touched.investmentFee && !!errors.investmentFee}
                    helperText={errors.investmentFee}
                    variant="outlined"
                    slotProps={{
                      htmlInput: {
                        min: "0",
                        max: "100",
                        step: "0.01"
                      }
                    }}
                  />
                </Grid>

                {/* Status Section */}
                <Grid size={{ xs: 12 }}>
                  <Typography variant="h6" gutterBottom sx={{ mt: 3, mb: 2, borderBottom: `1px solid ${theme.palette.divider}`, pb: 1 }}>
                    Status
                  </Typography>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <FormControl fullWidth error={touched.investmentStatus && !!errors.investmentStatus}>
                    <InputLabel id="investment-status-label">Investment Status</InputLabel>
                    <Select
                      name="investmentStatus"
                      labelId="investment-status-label"
                      id="investment_status"
                      label="Investment Status"
                      required
                      value={values.investmentStatus}
                      onChange={handleChange}
                      onBlur={handleBlur}
                    >
                      <MenuItem value="Active">Active</MenuItem>
                      <MenuItem value="Inactive">Inactive</MenuItem>
                      <MenuItem value="Closed">Closed</MenuItem>
                    </Select>
                    <FormHelperText>{errors.investmentStatus}</FormHelperText>
                  </FormControl>
                </Grid>

                {/* Action Buttons Section */}
                <Grid size={{ xs: 12 }}>
                  <Box sx={{ display: 'flex', gap: 2, mt: 4, pt: 2, borderTop: `1px solid ${theme.palette.divider}`, justifyContent: 'center' }}>
                    <Button
                      type="button"
                      variant="outlined"
                      color="secondary"
                      size="large"
                      onClick={() => resetForm()}
                      sx={{ minWidth: 120 }}
                    >
                      Clear Form
                    </Button>
                    <Button
                      type="button"
                      variant="contained"
                      color="primary"
                      size="large"
                      onClick={handleDialogOpen}
                      sx={{ minWidth: 120 }}
                    >
                      Add Investment
                    </Button>
                  </Box>
                </Grid>

              </Grid>
            </Box>

            {/* API Message */}
            {apiMessage && (
              <Box sx={{ mt: 3 }}>
                <Typography
                  variant="body1"
                  color={apiMessage.startsWith("Error") ? "error" : "success"}
                  sx={{ textAlign: 'center', fontWeight: 'medium' }}
                >
                  {apiMessage}
                </Typography>
              </Box>
            )}
          </form>

          {/* Confirmation Dialog */}
          <DialogComponent
            open={isDialogOpen}
            onClose={handleDialogClose}
            mainHeading="Please confirm Investment Details"
            headings={[
              "Institution Name:",
              "Initial Investment Date",
              "Investment Type:",
              "Investment Name:",
              "Investment Ticker:",
              "Currency:",
              "Initial Unit Price:",
              "Current Unit Price:",
              "Number of Units Held:",
              "Total Dividends Received:",
              "Total Tax Paid:",
              "Total Fees Paid:",
              "Investment Fee (%):",
              "Investment Status:"
            ]}
            values={dialogValues}
            buttons={[
              {
                label: "Confirm",
                onClick: async () => {
                  handleSubmit();
                  handleDialogClose();
                },
                variant: "contained",
                color: "primary",
              },
              {
                label: "Edit",
                onClick: handleDialogClose,
                variant: "outlined",
                color: "secondary",
              },
              {
                label: "Cancel and Clear",
                onClick: () => {
                  resetForm();
                  handleDialogClose();
                },
                variant: "outlined",
                color: "secondary",
              },
            ]}
          />
        </Container>
      </div>
    </ThemeProvider>
  )
}
