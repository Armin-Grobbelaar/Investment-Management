"use client";

import React, { useState, useRef, useCallback } from "react";
import axios from "axios";
import {
    Box, Container, Grid, Card, CardContent, Typography, Button, IconButton,
    LinearProgress, Alert, AlertTitle, Chip, Divider, Paper, Tabs, Tab,
    Table, TableBody, TableCell, TableHead, TableRow, TableContainer,
    Tooltip, CircularProgress, ToggleButton, ToggleButtonGroup
} from "@mui/material";
import { ThemeProvider } from "@mui/material/styles";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DownloadIcon from "@mui/icons-material/Download";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import SkipNextIcon from "@mui/icons-material/SkipNext";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import ReceiptIcon from "@mui/icons-material/Receipt";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import Link from "next/link";
import { brandingDarkTheme, brandingLightTheme } from "../Themes/muiTheme";
import DrawerComponent from "../Reusable Components/Drawers/SideMenyDrawer";

// ── Types ────────────────────────────────────────────────────────────────────
type ImportType = "investments" | "transactions" | "unit_prices" | "mixed";

interface ImportResult {
    imported: number;
    skipped: number;
    errors: string[];
    import_type: string;
    total_rows: number;
    timestamp: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────
const TYPE_CONFIG: Record<ImportType, { label: string; icon: React.ReactNode; color: string; description: string; example: string[] }> = {
    investments: {
        label: "Investments",
        icon: <TrendingUpIcon />,
        color: "#007FFF",
        description: "Import multiple investment portfolios at once. One investment per row.",
        example: ["institution_name", "investment_name", "investment_ticker", "investment_type", "unit_currency", "initial_investment_date", "initial_unit_price", "unit_price", "number_of_units_held", "total_dividends_received", "total_tax_paid", "total_fees_paid", "investment_fee", "investment_status"],
    },
    transactions: {
        label: "Transactions",
        icon: <ReceiptIcon />,
        color: "#00C853",
        description: "Import buy/sell transactions for existing investments. Matches by investment_name.",
        example: ["investment_name", "transaction_date", "transaction_type", "transaction_amount"],
    },
    unit_prices: {
        label: "Unit Prices",
        icon: <ShowChartIcon />,
        color: "#FF6B35",
        description: "Import historical unit prices for existing investments. Matches by investment_name.",
        example: ["investment_name", "unit_price_date", "unit_price"],
    },
    mixed: {
        label: "Auto-Detect",
        icon: <AutorenewIcon />,
        color: "#9C27B0",
        description: "Automatically detect the import type from your CSV column headers.",
        example: ["(auto-detected)"],
    },
};

// ── Drag & Drop Upload Zone ──────────────────────────────────────────────────
const UploadZone = ({
    onFile, darkMode, loading, accept = ".csv,.txt"
}: {
    onFile: (f: File) => void;
    darkMode: boolean;
    loading: boolean;
    accept?: string;
}) => {
    const [dragging, setDragging] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f) onFile(f);
    }, [onFile]);

    const borderColor = dragging ? "#007FFF" : darkMode ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.12)";

    return (
        <Box
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => !loading && inputRef.current?.click()}
            sx={{
                border: `2px dashed ${borderColor}`,
                borderRadius: 3, p: 6, textAlign: "center", cursor: loading ? "default" : "pointer",
                transition: "all 0.2s",
                backgroundColor: dragging
                    ? (darkMode ? "rgba(0,127,255,0.08)" : "rgba(0,127,255,0.04)")
                    : "transparent",
                "&:hover": !loading ? {
                    borderColor: "#007FFF",
                    backgroundColor: darkMode ? "rgba(0,127,255,0.06)" : "rgba(0,127,255,0.03)"
                } : {}
            }}
        >
            <input ref={inputRef} type="file" accept={accept} style={{ display: "none" }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
            {loading
                ? <CircularProgress size={48} sx={{ mb: 2 }} />
                : <CloudUploadIcon sx={{ fontSize: 64, color: "#007FFF", opacity: 0.7, mb: 1 }} />
            }
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                {loading ? "Processing…" : "Drop CSV here or click to browse"}
            </Typography>
            <Typography variant="body2" color="textSecondary">
                Supports CSV files exported from Excel or any spreadsheet
            </Typography>
        </Box>
    );
};

// ── Main Component ────────────────────────────────────────────────────────────
export default function BulkImport() {
    const [darkMode, setDarkMode] = useState(false);
    const [importType, setImportType] = useState<ImportType>("investments");
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<ImportResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Price fetch state
    const [priceLoading, setPriceLoading] = useState(false);
    const [priceMsg, setPriceMsg] = useState<string | null>(null);

    const menuItems = [
        { heading: "Navigation", items: ["Dashboard", "Net Worth", "IRR Analysis", "Metrics", "Predictions", "Edit Data", "Bulk Import"], urls: ["/Investments", "/NetWorth", "/IRRAnalysis", "/ViewInvestmentMetrics", "/ViewInvestmentPredictions", "/EditInvestmentData", "/BulkImport"] }
    ];

    const theme = darkMode ? brandingDarkTheme : brandingLightTheme;
    const bg = darkMode ? "#001E3C" : "#fff";
    const cardBg = darkMode ? "#0A1929" : "#ffffff";
    const textPrimary = darkMode ? "#ffffff" : "#1A2027";
    const textSecondary = darkMode ? "#B2BAC2" : "#6F7E8C";
    const borderColor = darkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)";

    const cfg = TYPE_CONFIG[importType];

    const handleFile = (file: File) => {
        setSelectedFile(file);
        setResult(null);
        setError(null);
    };

    const handleUpload = async () => {
        if (!selectedFile) return;
        setLoading(true);
        setError(null);
        setResult(null);

        const form = new FormData();
        form.append("file", selectedFile);
        form.append("import_type", importType);

        try {
            const res = await axios.post(`/api/bulk_import/Investments`, form, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            setResult(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || "Upload failed");
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadTemplate = async (type: ImportType) => {
        if (type === "mixed") return;
        try {
            const res = await axios.get(`/api/bulk_import/template/${type}`, {
                responseType: "blob"
            });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const a = document.createElement("a");
            a.href = url;
            a.download = `template_${type}.csv`;
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error("Download failed", err);
        }
    };

    const handleFetchPrices = async () => {
        setPriceLoading(true);
        setPriceMsg(null);
        try {
            await axios.post("/api/prices/fetch/Investments");
            setPriceMsg("✅ Price fetch started in the background. Check the server logs for progress.");
        } catch (err: any) {
            setPriceMsg(`❌ Error: ${err.response?.data?.detail || err.message}`);
        } finally {
            setPriceLoading(false);
        }
    };

    return (
        <ThemeProvider theme={theme}>
            <Box sx={{ minHeight: "100vh", backgroundColor: bg, transition: "background-color 0.3s" }}>

                {/* Top bar */}
                <Box sx={{ display: "flex", alignItems: "center", p: 1, gap: 1, borderBottom: `1px solid ${borderColor}` }}>
                    <DrawerComponent menuItems={menuItems} />
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, ml: 1 }}>
                        <CloudUploadIcon sx={{ color: "#007FFF", fontSize: 28 }} />
                        <Typography variant="h6" sx={{ fontWeight: 700, color: textPrimary, letterSpacing: "-0.5px" }}>
                            Bulk Import
                        </Typography>
                    </Box>
                    <Box sx={{ flex: 1 }} />
                    <IconButton onClick={() => setDarkMode(d => !d)} sx={{ color: textSecondary }}>
                        {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
                    </IconButton>
                </Box>

                <Container maxWidth="xl" sx={{ py: 4 }}>
                    <Grid container spacing={3}>

                        {/* ── Import type selector ── */}
                        <Grid size={{ xs: 12 }}>
                            <Typography variant="h6" sx={{ fontWeight: 700, color: textPrimary, mb: 2 }}>
                                What would you like to import?
                            </Typography>
                            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                                {(Object.keys(TYPE_CONFIG) as ImportType[]).map(type => {
                                    const c = TYPE_CONFIG[type];
                                    const active = importType === type;
                                    return (
                                        <Card key={type} elevation={0} onClick={() => { setImportType(type); setSelectedFile(null); setResult(null); setError(null); }} sx={{
                                            border: `2px solid ${active ? c.color : borderColor}`,
                                            borderRadius: 3, p: 1, cursor: "pointer", flex: "1 1 200px", minWidth: 160,
                                            backgroundColor: active ? c.color + "11" : cardBg,
                                            transition: "all 0.2s",
                                            "&:hover": { borderColor: c.color, backgroundColor: c.color + "08" }
                                        }}>
                                            <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                                                <Box sx={{ color: c.color, mb: 1 }}>{c.icon}</Box>
                                                <Typography variant="subtitle1" sx={{ fontWeight: 700, color: textPrimary }}>
                                                    {c.label}
                                                </Typography>
                                                <Typography variant="caption" sx={{ color: textSecondary, lineHeight: 1.4 }}>
                                                    {c.description}
                                                </Typography>
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </Box>
                        </Grid>

                        {/* ── Required columns ── */}
                        <Grid size={{ xs: 12, md: 4 }}>
                            <Card elevation={0} sx={{ backgroundColor: cardBg, borderRadius: 3, border: `1px solid ${borderColor}`, height: "100%" }}>
                                <CardContent sx={{ p: 3 }}>
                                    <Typography variant="subtitle1" sx={{ fontWeight: 700, color: textPrimary, mb: 2 }}>
                                        Required CSV Columns
                                    </Typography>
                                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.8, mb: 3 }}>
                                        {cfg.example.map(col => (
                                            <Chip key={col} label={col} size="small" sx={{
                                                backgroundColor: cfg.color + "18", color: cfg.color,
                                                fontFamily: "monospace", fontSize: 11, fontWeight: 600
                                            }} />
                                        ))}
                                    </Box>
                                    {importType !== "mixed" && (
                                        <Button
                                            startIcon={<DownloadIcon />}
                                            variant="outlined"
                                            size="small"
                                            fullWidth
                                            onClick={() => handleDownloadTemplate(importType)}
                                            sx={{ borderColor: cfg.color, color: cfg.color, "&:hover": { borderColor: cfg.color } }}
                                        >
                                            Download Template
                                        </Button>
                                    )}
                                    <Divider sx={{ my: 2 }} />
                                    <Typography variant="caption" sx={{ color: textSecondary, display: "block", lineHeight: 1.6 }}>
                                        💡 <b>Tips:</b><br />
                                        • First row must be headers<br />
                                        • Dates: YYYY-MM-DD format<br />
                                        • Numbers: no currency symbols<br />
                                        • Investment names must match exactly for transactions/prices<br />
                                        • Duplicate investments are skipped automatically
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>

                        {/* ── Upload zone ── */}
                        <Grid size={{ xs: 12, md: 8 }}>
                            <Card elevation={0} sx={{ backgroundColor: cardBg, borderRadius: 3, border: `1px solid ${borderColor}` }}>
                                <CardContent sx={{ p: 3 }}>
                                    <UploadZone onFile={handleFile} darkMode={darkMode} loading={loading} />

                                    {selectedFile && !loading && (
                                        <Box sx={{ mt: 2, display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
                                            <Chip
                                                icon={<CheckCircleIcon />}
                                                label={`${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)`}
                                                color="success" variant="outlined"
                                            />
                                            <Box sx={{ flex: 1 }} />
                                            <Button
                                                variant="contained"
                                                size="large"
                                                startIcon={<CloudUploadIcon />}
                                                onClick={handleUpload}
                                                disabled={loading}
                                                sx={{
                                                    background: `linear-gradient(135deg, ${cfg.color} 0%, ${cfg.color}cc 100%)`,
                                                    fontWeight: 700, px: 4
                                                }}
                                            >
                                                Import {cfg.label}
                                            </Button>
                                        </Box>
                                    )}

                                    {loading && <LinearProgress sx={{ mt: 2, borderRadius: 1 }} />}
                                </CardContent>
                            </Card>
                        </Grid>

                        {/* ── Error ── */}
                        {error && (
                            <Grid size={{ xs: 12 }}>
                                <Alert severity="error" sx={{ borderRadius: 2 }}>
                                    <AlertTitle>Import Failed</AlertTitle>
                                    {error}
                                </Alert>
                            </Grid>
                        )}

                        {/* ── Results ── */}
                        {result && (
                            <Grid size={{ xs: 12 }}>
                                <Card elevation={0} sx={{ backgroundColor: cardBg, borderRadius: 3, border: `1px solid ${borderColor}` }}>
                                    <CardContent sx={{ p: 3 }}>
                                        <Typography variant="h6" sx={{ fontWeight: 700, color: textPrimary, mb: 3 }}>
                                            Import Results
                                        </Typography>
                                        <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap", mb: 3 }}>
                                            {[
                                                { icon: <CheckCircleIcon />, color: "#00C853", label: "Imported", value: result.imported },
                                                { icon: <SkipNextIcon />, color: "#FFB700", label: "Skipped (duplicates)", value: result.skipped },
                                                { icon: <ErrorIcon />, color: "#F44336", label: "Errors", value: result.errors.length },
                                                { icon: null, color: textSecondary, label: "Total Rows", value: result.total_rows },
                                            ].map((stat, i) => (
                                                <Box key={i} sx={{ textAlign: "center", minWidth: 100 }}>
                                                    {stat.icon && <Box sx={{ color: stat.color, mb: 0.5 }}>{stat.icon}</Box>}
                                                    <Typography variant="h4" sx={{ fontWeight: 800, color: stat.color }}>
                                                        {stat.value}
                                                    </Typography>
                                                    <Typography variant="caption" sx={{ color: textSecondary }}>
                                                        {stat.label}
                                                    </Typography>
                                                </Box>
                                            ))}
                                        </Box>

                                        {result.errors.length > 0 && (
                                            <>
                                                <Divider sx={{ mb: 2 }} />
                                                <Typography variant="subtitle2" sx={{ color: "#F44336", mb: 1, fontWeight: 600 }}>
                                                    Errors (first {Math.min(result.errors.length, 20)} shown):
                                                </Typography>
                                                <TableContainer component={Paper} elevation={0} sx={{ maxHeight: 300, border: `1px solid ${borderColor}`, borderRadius: 2 }}>
                                                    <Table size="small">
                                                        <TableBody>
                                                            {result.errors.slice(0, 20).map((err, i) => (
                                                                <TableRow key={i}>
                                                                    <TableCell sx={{ color: "#F44336", fontFamily: "monospace", fontSize: 12 }}>
                                                                        {err}
                                                                    </TableCell>
                                                                </TableRow>
                                                            ))}
                                                        </TableBody>
                                                    </Table>
                                                </TableContainer>
                                            </>
                                        )}

                                        {result.imported > 0 && result.errors.length === 0 && (
                                            <Alert severity="success" sx={{ mt: 2, borderRadius: 2 }}>
                                                Successfully imported {result.imported} {result.import_type.replace("_", " ")}! The dashboard will reflect the changes shortly.
                                            </Alert>
                                        )}
                                    </CardContent>
                                </Card>
                            </Grid>
                        )}

                        {/* ── Price Fetch Control ── */}
                        <Grid size={{ xs: 12 }}>
                            <Card elevation={0} sx={{
                                background: "linear-gradient(135deg, #001E3C 0%, #173A5E 50%, #0059B2 100%)",
                                borderRadius: 3
                            }}>
                                <CardContent sx={{ p: 3 }}>
                                    <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 3 }}>
                                        <Box>
                                            <Typography variant="h6" sx={{ color: "#fff", fontWeight: 700, mb: 0.5 }}>
                                                📈 Automated Unit Price Fetching
                                            </Typography>
                                            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.65)", maxWidth: 600, lineHeight: 1.7 }}>
                                                The system automatically fetches current prices daily at <b style={{ color: "#fff" }}>11:30 SAST</b> using yfinance 
                                                (for JSE ETFs/shares with <code style={{ color: "#69ff47" }}>.JO</code> suffix) and fundsdata.co.za (for SA unit trust codes like <code style={{ color: "#69ff47" }}>AGBF</code>). 
                                                Historical prices are back-filled in batches of 15/day per investment to avoid overloading sources.
                                                You can also trigger a manual fetch below.
                                            </Typography>
                                        </Box>
                                        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, minWidth: 220 }}>
                                            <Button
                                                variant="contained"
                                                startIcon={priceLoading ? <CircularProgress size={16} sx={{ color: "#fff" }} /> : <AutorenewIcon />}
                                                onClick={handleFetchPrices}
                                                disabled={priceLoading}
                                                sx={{ background: "rgba(0,127,255,0.9)", fontWeight: 700, "&:hover": { background: "#007FFF" } }}
                                            >
                                                {priceLoading ? "Starting…" : "Fetch Prices Now"}
                                            </Button>
                                            <Link href="/Investments" style={{ textDecoration: "none" }}>
                                                <Button variant="outlined" fullWidth sx={{ borderColor: "rgba(255,255,255,0.3)", color: "#fff" }}>
                                                    View Dashboard
                                                </Button>
                                            </Link>
                                        </Box>
                                    </Box>
                                    {priceMsg && (
                                        <Alert severity={priceMsg.startsWith("✅") ? "success" : "error"} sx={{ mt: 2, borderRadius: 2 }}>
                                            {priceMsg}
                                        </Alert>
                                    )}
                                </CardContent>
                            </Card>
                        </Grid>

                    </Grid>
                </Container>
            </Box>
        </ThemeProvider>
    );
}
