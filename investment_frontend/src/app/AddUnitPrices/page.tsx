"use client";
import axios from "axios";
import React, { useState } from "react";
import { Container, Typography, MenuItem, Select, FormControl, InputLabel, Button, Box, SelectChangeEvent, ThemeProvider, IconButton } from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme'
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';

const InvestmentUnitPriceUpload = () => {
    const [darkMode, setDarkMode] = useState(false);
  const [selectedInvestment, setSelectedInvestment] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);

  const investments = ["Investment A", "Investment B", "Sygnia Itrix MSCI USA Index ETF"]; // Example investments

  const handleInvestmentChange = (event: SelectChangeEvent<string>) => {
    setSelectedInvestment(event.target.value);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleDragEnter = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);

    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      setSelectedFile(event.dataTransfer.files[0]);
    }
  };

  const handleFileUpload = () => {
    if (!selectedInvestment || !selectedFile) {
      alert("Please select an investment and a CSV file.");
      return;
    }

    console.log("Uploading file:", selectedFile.name, "for investment:", selectedInvestment);

    const formData = new FormData();
    formData.append("investment", selectedInvestment);
    formData.append("file", selectedFile);

    fetch("http://127.0.0.1:3337/import_unit_prices/", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("File uploaded successfully:", data);
      })
      .catch((error) => {
        console.error("Error uploading file:", error);
      });
  };

  const toggleDarkMode = () => {
    setDarkMode(prevMode => !prevMode);
  };

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
    <Container maxWidth="sm" sx={{ mt: 4 }}>
    <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
              {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>
      <Typography variant="h4" gutterBottom align="center">
        Upload Unit Prices
      </Typography>

      <FormControl fullWidth sx={{ mb: 3 }}>
        <InputLabel id="investment-select-label">Select Investment</InputLabel>
        <Select
          labelId="investment-select-label"
          value={selectedInvestment}
          onChange={handleInvestmentChange}
        >
          {investments.map((investment) => (
            <MenuItem key={investment} value={investment}>
              {investment}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <Box
        onDragEnter={handleDragEnter}
        onDragOver={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        sx={{
          border: "2px dashed #1976d2",
          borderRadius: "8px",
          padding: "20px",
          textAlign: "center",
          backgroundColor: dragActive ? "#e3f2fd" : "transparent",
        }}
      >
        <Typography variant="body1" gutterBottom>
          {selectedFile ? selectedFile.name : "Drag and drop your CSV file here or click to browse"}
        </Typography>
        <Button
          variant="contained"
          startIcon={<CloudUploadIcon />}
          component="label"
        >
          Choose File
          <input
            type="file"
            accept=".csv"
            hidden
            onChange={handleFileSelect}
          />
        </Button>
      </Box>

      <Button
        variant="contained"
        color="primary"
        fullWidth
        sx={{ mt: 3 }}
        onClick={handleFileUpload}
        disabled={!selectedInvestment || !selectedFile}
      >
        Upload
      </Button>
    </Container>
    </ThemeProvider>
  );
};

export default InvestmentUnitPriceUpload;