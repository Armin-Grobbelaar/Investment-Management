"use client";

import axios from "axios";
import React, { useState } from "react";
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
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import { brandingDarkTheme, brandingLightTheme } from "../Themes/muiTheme";

const InvestmentUnitPriceUpload = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [selectedInvestment, setSelectedInvestment] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);

  const investments = [
    "Investment A",
    "Investment B",
    "Sygnia Itrix MSCI USA Index ETF",
  ]; // Example investments

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
    if (!selectedInvestment || !selectedFile) {
      alert("Please select an investment and a CSV file.");
      return;
    }

    console.log(
      "Uploading file:",
      selectedFile.name,
      "for investment:",
      selectedInvestment
    );

    const formData = new FormData();
    formData.append("investment_name", selectedInvestment);
    formData.append("file", selectedFile);

    try {
      const response = await axios.post(
        "http://localhost:3337/import_unit_prices/",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );
      console.log("File uploaded successfully:", response.data);
      alert(`Upload successful: ${response.data.message}`);
      setSelectedFile(null); // reset file
    } catch (error: any) {
      if (error.response) {
        console.error("Server error:", error.response.data);
        alert(`Server error: ${JSON.stringify(error.response.data)}`);
      } else if (error.request) {
        console.error("No response received:", error.request);
        alert("No response from server. Check backend & CORS.");
      } else {
        console.error("Error setting up request:", error.message);
        alert(`Error: ${error.message}`);
      }
    }
  };

  const toggleDarkMode = () => setDarkMode((prev) => !prev);

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
      <Container maxWidth="sm" sx={{ mt: 4, position: "relative" }}>
        <IconButton
          onClick={toggleDarkMode}
          color="inherit"
          style={{ position: "absolute", top: "10px", right: "10px" }}
        >
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
          disabled={!selectedInvestment || !selectedFile}
        >
          Upload
        </Button>
      </Container>
    </ThemeProvider>
  );
};

export default InvestmentUnitPriceUpload;