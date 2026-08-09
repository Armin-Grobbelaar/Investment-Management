"use client";

import axios from "axios";
import React, { useState, useEffect } from "react";
import {
  Container,
  Typography,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Button,
  Box,
  SelectChangeEvent,
  ThemeProvider,
  IconButton,
  Alert,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import { brandingDarkTheme, brandingLightTheme } from "../Themes/muiTheme";

const AddInvestmentData = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [selectedDataType, setSelectedDataType] = useState<string>("");
  const [selectedInvestment, setSelectedInvestment] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [investments, setInvestments] = useState<string[]>([]);
  const [dataTypes, setDataTypes] = useState<string[]>([]);

  useEffect(() => {
    fetchInvestments();
    fetchDataTypes();
  }, []);

  const fetchInvestments = async () => {
    try {
      console.log('Fetching investment names from API...');
      const response = await axios.get("/api/investment_names");
      console.log('API Response:', response.data);
      console.log('Investment names received:', response.data.investment_names || []);
      setInvestments(response.data.investment_names || []);
    } catch (error) {
      console.error('Error fetching investments:', error);
      setInvestments([]);
    }
  };

  const fetchDataTypes = async () => {
    try {
      const response = await axios.get("/api/edit_data/tables/Investments");
      // Filter to only show relevant data types for upload
      const allowedDataTypes = ['unit_prices', 'transactions', 'returns', 'dividends', 'fees', 'tax', 'inflation'];
      const filteredTypes = response.data.tables.filter((table: string) => allowedDataTypes.includes(table));
      // Add mixed option manually
      setDataTypes([...filteredTypes, 'mixed']);
    } catch (error) {
      console.error('Error fetching data types:', error);
    }
  };

  const handleDataTypeChange = (event: SelectChangeEvent<string>) => {
    setSelectedDataType(event.target.value);
  };

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


  const handleFileUpload = async () => {
    if (!selectedDataType || !selectedInvestment || !selectedFile) {
      alert("Please select data type, investment, and a CSV file.");
      return;
    }

    console.log(
      "Uploading file:",
      selectedFile.name,
      "data type:",
      selectedDataType,
      "for investment:",
      selectedInvestment
    );

    const formData = new FormData();
    formData.append("investment_name", selectedInvestment);
    formData.append("data_type", selectedDataType);
    formData.append("file", selectedFile);

    const endpoint = selectedDataType === 'unit_prices'
      ? "/api/import_unit_prices/"
      : `/api/import_investment_data/${selectedDataType}/`;

    try {
      const response = await axios.post(endpoint, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = response.data;
      alert(data.message);
      console.log('Upload response:', data);
      setSelectedFile(null);
      setSelectedDataType('');
      setSelectedInvestment('');
    } catch (error: any) {
      if (error.response && error.response.data) {
        const errData = error.response.data;
        alert(`Server error: ${JSON.stringify(errData)}`);
        console.error('Server error:', errData);
      } else if (error.request) {
        alert("No response from server. Check backend & CORS.");
        console.error('No response received:', error.request);
      } else {
        alert(`Error: ${error.message}`);
        console.error('Error setting up request:', error.message);
      }
    }
  };


  const toggleDarkMode = () => setDarkMode((prev) => !prev);

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
      <div style={{ backgroundColor: darkMode ? '#001E3C' : '#fff', minHeight: '100vh', transition: 'background-color 0.3s' }}>
        <IconButton
          onClick={toggleDarkMode}
          color="inherit"
          style={{ position: "absolute", top: "10px", right: "10px" }}
        >
          {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
        </IconButton>
        <Container maxWidth="sm" sx={{ mt: 4, position: "relative" }}>

          <Typography variant="h4" gutterBottom align="center">
            Add Investment Data
          </Typography>

          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel id="datatype-select-label">Select Data Type</InputLabel>
            <Select
              labelId="datatype-select-label"
              value={selectedDataType}
              onChange={handleDataTypeChange}
            >
              {dataTypes.map((dataType) => (
                <MenuItem key={dataType} value={dataType}>
                  {dataType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

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
              mb: 2,
            }}
          >
            <Typography variant="body1" gutterBottom>
              {selectedFile
                ? selectedFile.name
                : "Drag and drop your CSV file here or click to browse"}
            </Typography>
            <Button variant="contained" startIcon={<CloudUploadIcon />} component="label">
              Choose File
              <input type="file" accept=".csv" hidden onChange={handleFileSelect} />
            </Button>
          </Box>

          <Button
            variant="contained"
            color="primary"
            fullWidth
            sx={{ mt: 1 }}
            onClick={handleFileUpload}
            disabled={!selectedDataType || !selectedInvestment || !selectedFile}
          >
            Upload
          </Button>
        </Container>
      </div>
    </ThemeProvider>
  );
};

export default AddInvestmentData;
