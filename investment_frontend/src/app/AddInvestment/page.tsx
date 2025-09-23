"use client";
import { Button, Container, FormControl, Grid, IconButton, MenuItem, Select, TextField, ThemeProvider, Typography, useTheme } from '@mui/material'
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
import { string } from 'yup';

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
        const response = await fetch("http://127.0.0.1:3337/add_investment/Investments", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            database_name: values.databaseName,
            institution_name: values.institutionsName,
            initial_investment_date: values.initialInvestmentDate.format("YYYY/MM/DD"),
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
      <Container>
      <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
              {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>
        <form onSubmit={handleSubmit}>
         <Grid container spacing={2} style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', transition: 'background-color 0.3s' }}>
           <Grid item xs={12} md={6}>
             <TextField name="institutionsName" label="Institution's Name" required fullWidth value={values.institutionsName} onChange={handleChange} onBlur={handleBlur} error={touched.institutionsName && !!errors.institutionsName} helperText={errors.institutionsName} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }}/>
           </Grid>
           <Grid item xs={12} md={6}>
             <TextField name="investmentName" label="Investment Name" required fullWidth value={values.investmentName} onChange={handleChange} onBlur={handleBlur} error={touched.investmentName && !!errors.investmentName} helperText={errors.investmentName} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }}/>
           </Grid>
           <Grid item xs={12} md={6}>
             <TextField name="investmentTicker" label="Investment Ticker/Class" required fullWidth value={values.investmentTicker} onChange={handleChange} onBlur={handleBlur} error={touched.investmentTicker && !!errors.investmentTicker} helperText={errors.investmentTicker} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }}/>
           </Grid>
           <Grid item xs={12} md={6}>
            <FormControl fullWidth error={touched.investmentType && !!errors.investmentType}>
             <Select
               name="investmentType"
               id="investment_type"
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
             </Select>
             {touched.investmentType && errors.investmentType && (
               <Typography variant="caption" color="error">
                 {errors.investmentType}
               </Typography>
             )}
           </FormControl>
           </Grid>
           <Grid item xs={12} md={6}>
           <FormControl fullWidth error={touched.unitCurrency && !!errors.unitCurrency}>
            <Select
              name="unitCurrency" // Add the name attribute
              labelId="unit-currency-label"
              id="unit_currency"
              required
              value={values.unitCurrency}
              onChange={handleChange}
              onBlur={handleBlur}
            >
              <MenuItem value="R">R</MenuItem>
              <MenuItem value="$">$</MenuItem>
              <MenuItem value="£">£</MenuItem>
              <MenuItem value="€">€</MenuItem>
              </Select>
             {touched.unitCurrency && errors.unitCurrency && (
               <Typography variant="caption" color="error">
                 {errors.unitCurrency}
               </Typography>
             )}
          </FormControl>
           </Grid>
           <Grid item xs={12} md={6}>
             <TextField name="initialUnitPrice" label="Initial Unit Price" type="number" required fullWidth value={values.initialUnitPrice} onChange={handleChange} onBlur={handleBlur} error={touched.initialUnitPrice && !!errors.initialUnitPrice} helperText={errors.initialUnitPrice} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }}/>
           </Grid>
           <Grid item xs={12} md={6}>
             <TextField name="currentUnitPrice" label="Current Unit Price" type="number" required fullWidth value={values.currentUnitPrice} onChange={handleChange} onBlur={handleBlur} error={touched.currentUnitPrice && !!errors.currentUnitPrice} helperText={errors.currentUnitPrice} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }}/>
           </Grid>
           <Grid item xs={12} md={6}>
             <TextField name="numberOfUnitsHeld" label="Number of Units Held" type="number" required fullWidth value={values.numberOfUnitsHeld} onChange={handleChange} onBlur={handleBlur} error={touched.numberOfUnitsHeld && !!errors.numberOfUnitsHeld} helperText={errors.numberOfUnitsHeld} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }}/>
           </Grid>
           <Grid item xs={12} md={6}>
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
               />
              </LocalizationProvider>
             </FormControl>
           </Grid>
           <Grid item xs={12} md={6}>
             <TextField name="totalDividends" label="Total Dividends Received" type="number" required fullWidth value={values.totalDividends} onChange={handleChange} onBlur={handleBlur} error={touched.totalDividends && !!errors.totalDividends} helperText={errors.totalDividends} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }}/>
           </Grid>
           <Grid item xs={12} md={6}>
             <TextField name="totalFees" label="Total Fees Paid" type="number" required fullWidth value={values.totalFees} onChange={handleChange} onBlur={handleBlur} error={touched.totalFees && !!errors.totalFees} helperText={errors.totalFees} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }}/>
           </Grid>
           <Grid item xs={12} md={6}>
             <TextField name="totalTax" label="Total Tax Paid" type="number" required fullWidth value={values.totalTax} onChange={handleChange} onBlur={handleBlur} error={touched.totalTax && !!errors.totalTax} helperText={errors.totalTax} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }} />
           </Grid>
           <Grid item xs={12} md={6}>
             <TextField name="investmentFee" label="Investment Fee (%)" type="number" required fullWidth value={values.investmentFee} onChange={handleChange} onBlur={handleBlur} error={touched.investmentFee && !!errors.investmentFee} helperText={errors.investmentFee} sx={{ '& .MuiInput-root.Mui-error': { color: theme.palette.error.main } }}/>
          </Grid>
          <Grid item xs={12} md={6}>
          <FormControl fullWidth error={touched.investmentStatus && !!errors.investmentStatus}>
            <Select
              name="investmentStatus" // Add the name attribute
              labelId="investment-status-label"
              id="investment_status"
              required
              value={values.investmentStatus}
              onChange={handleChange}
              onBlur={handleBlur}
            >
              <MenuItem value="Active">Active</MenuItem>
              <MenuItem value="Inactive">Inactive</MenuItem>
              <MenuItem value="Closed">Closed</MenuItem>
              </Select>
             {touched.investmentStatus && errors.investmentStatus && (
               <Typography variant="caption" color="error">
                 {errors.investmentStatus}
               </Typography>
             )}
          </FormControl>
          </Grid>
           </Grid>
          <Grid item xs={12} md={6}>
          <Button variant="contained" onClick={handleDialogOpen} >Add Investment</Button>
          </Grid>
          <Grid item xs={12} md={6}>
          <Button variant="contained">Clear</Button>
          </Grid>
        </form>
        <DialogComponent
          open={isDialogOpen}
          onClose={handleDialogClose}
          mainHeading="Please confirm Investment Details"
          headings={["Institution's Name:", "Initial Investment Date", "Investment Type:", "Investment Name:", "Investment Ticker:",  "Investment Currency:", "Initial Unit Price:", "Current Unit Price:", "Number of Units Held:", "Total Dividends Paid:", "Total Tax Paid:", "Total Fees Paid:", "Investment Fee:", "Investment Status"]} // Example headings
          values={dialogValues} // Example corresponding values
          buttons={[
            {
              label: "Confirm",
              onClick: async () => {
                handleSubmit(); // Wait for form submission
                console.log("Form submitted");
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
              label: "Cancel and clear form",
              onClick: () => {
                resetForm();
                handleDialogClose();
              },
              variant: "outlined",
              color: "secondary",
            },
          ]}
        />
        {apiMessage && (
          <Typography color={apiMessage.startsWith("Error") ? "error" : "primary"}>{apiMessage}</Typography>
        )}
      </Container>
    </ThemeProvider>
  )
}
