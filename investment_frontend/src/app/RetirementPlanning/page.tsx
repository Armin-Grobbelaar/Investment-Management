"use client";
import React, { useEffect, useState, useCallback } from "react";
import {
  Box, Container, Grid, Paper, Typography, TextField, Slider, Button,
  CircularProgress, Chip, Divider, Tooltip, IconButton, Switch,
  FormControlLabel, Accordion, AccordionSummary, AccordionDetails,
  Tab, Tabs, Alert, Card, CardContent, LinearProgress, Snackbar
} from "@mui/material";
import { ThemeProvider } from "@mui/material/styles";
import axios from "axios";
import { useRouter } from "next/navigation";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
  Legend, ResponsiveContainer, ReferenceLine
} from "recharts";
import KeyboardBackspaceIcon from "@mui/icons-material/KeyboardBackspace";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import CalculateIcon from "@mui/icons-material/Calculate";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import AccountBalanceIcon from "@mui/icons-material/AccountBalance";
import LocalFireDepartmentIcon from "@mui/icons-material/LocalFireDepartment";
import DrawerComponent from "../Reusable Components/Drawers/SideMenyDrawer";
import { brandingDarkTheme, brandingLightTheme } from "../Themes/muiTheme";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Scenario {
  label: string;
  monthly_contribution: number;
  total_at_retirement: number;
  total_contributed: number;
  living_annuity_capital: number;
  life_annuity_capital: number;
  living_income_monthly: number;
  life_income_monthly: number;
  total_monthly_income: number;
  living_income_monthly_real: number;
  life_income_monthly_real: number;
  total_monthly_income_real: number;
  yearly_series: { year: number; portfolio_value: number; portfolio_value_real: number }[];
}

interface FireMetrics {
  fire_number_today: number;
  fire_number_at_retirement: number;
  lean_fire_today: number;
  lean_fire_at_retirement: number;
  fat_fire_today: number;
  fat_fire_at_retirement: number;
  coast_fire_today: number;
  projected_at_retirement: number;
  shortfall: number;
  extra_monthly_needed: number;
  months_to_fire: number | null;
  is_on_track: boolean;
  current_value: number;
  annual_expenses_today: number;
}

interface ProjectionResult {
  scenarios: Scenario[];
  fire_metrics: FireMetrics;
  calculation_inputs: Record<string, number | string>;
  formulas: Record<string, string>;
}

interface AutoInputs {
  current_portfolio_value: number;
  ra_irr_historical: number;
  avg_monthly_contribution: number;
  life_annuity_rate: number;
  default_inflation: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const fmt = (v: number, decimals = 0) =>
  new Intl.NumberFormat("en-ZA", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(v);

const fmtCurr = (v: number) =>
  new Intl.NumberFormat("en-ZA", { style: "currency", currency: "ZAR", maximumFractionDigits: 0 }).format(v);

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

const InfoTip = ({ text }: { text: string }) => (
  <Tooltip title={text} placement="top" arrow>
    <InfoOutlinedIcon sx={{ fontSize: 14, ml: 0.5, opacity: 0.6, cursor: "help", verticalAlign: "middle" }} />
  </Tooltip>
);

interface AutoFieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  useAuto?: boolean;
  setUseAuto?: (v: boolean) => void;
  unit?: string;
  tooltip?: string;
  disabled?: boolean;
  loadingAuto?: boolean;
}

const AutoField = ({
  label, value, onChange, useAuto, setUseAuto, unit = "%", tooltip, disabled = false, loadingAuto = false
}: AutoFieldProps) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (useAuto && setUseAuto) {
      setUseAuto(false);
    }
    onChange(e.target.value);
  };

  return (
    <Box mb={2}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={0.5}>
        <Typography variant="caption" color="text.secondary" fontWeight={600}>
          {label}
          {tooltip && <InfoTip text={tooltip} />}
        </Typography>
        {setUseAuto !== undefined && (
          <FormControlLabel
            control={<Switch size="small" checked={useAuto} onChange={(e) => setUseAuto(e.target.checked)} />}
            label={<Typography variant="caption" color={useAuto ? "primary" : "text.secondary"}>{useAuto ? "Auto" : "Manual"}</Typography>}
            sx={{ m: 0 }}
          />
        )}
      </Box>
      <TextField
        fullWidth
        size="small"
        value={value}
        onChange={handleChange}
        disabled={(useAuto ?? false) || disabled || loadingAuto}
        InputProps={{
          endAdornment: <Typography variant="caption" color="text.secondary">{unit}</Typography>,
          sx: { opacity: useAuto ? 0.65 : 1 },
        }}
        variant="outlined"
      />
    </Box>
  );
};

interface ScenarioCardProps {
  scenario: Scenario;
  idx: number;
  darkMode: boolean;
  livingSplit: number;
}

const ScenarioCard = ({ scenario, idx, darkMode, livingSplit }: ScenarioCardProps) => {
  const color = SCENARIO_COLORS[idx];
  return (
    <Card variant="outlined" sx={{
      borderColor: color,
      borderWidth: 2,
      borderRadius: 3,
      position: "relative",
      overflow: "visible",
      background: darkMode
        ? `linear-gradient(135deg, rgba(0,0,0,0.4) 0%, rgba(${idx === 0 ? "239,68,68" : idx === 1 ? "59,130,246" : "16,185,129"},0.08) 100%)`
        : "background.paper",
      boxShadow: `0 0 20px ${color}22`,
    }}>
      <Box sx={{
        position: "absolute", top: -14, left: 20,
        background: color, borderRadius: 10, px: 2, py: 0.3,
      }}>
        <Typography variant="caption" color="white" fontWeight={700}>{scenario.label}</Typography>
      </Box>
      <CardContent sx={{ pt: 3 }}>
        {/* Main income highlight */}
        <Box textAlign="center" mb={2} py={2} sx={{
          background: darkMode ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)",
          borderRadius: 2,
        }}>
          <Typography variant="caption" color="text.secondary">Total Monthly Income</Typography>
          <Typography variant="h4" fontWeight={800} sx={{ color }}>
            {fmtCurr(scenario.total_monthly_income)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Real (today's money): {fmtCurr(scenario.total_monthly_income_real)}
          </Typography>
        </Box>

        <Divider sx={{ mb: 1.5 }} />

        {/* Income breakdown */}
        <Box mb={1}>
          <Box display="flex" justifyContent="space-between" mb={0.5}>
            <Typography variant="body2" color="text.secondary">
              🏦 Living Annuity ({livingSplit}%)
              <InfoTip text="Drawdown income from your invested capital — you remain the owner." />
            </Typography>
            <Typography variant="body2" fontWeight={700}>{fmtCurr(scenario.living_income_monthly)}/mo</Typography>
          </Box>
          <Box display="flex" justifyContent="space-between" mb={0.5}>
            <Typography variant="body2" color="text.secondary">
              🔒 Life Annuity ({100 - livingSplit}%)
              <InfoTip text="Guaranteed income for life purchased from an insurer." />
            </Typography>
            <Typography variant="body2" fontWeight={700}>{fmtCurr(scenario.life_income_monthly)}/mo</Typography>
          </Box>
        </Box>

        <Divider sx={{ my: 1.5 }} />

        {/* At-retirement value */}
        <Box display="flex" justifyContent="space-between" mb={0.5}>
          <Typography variant="caption" color="text.secondary">Portfolio at Retirement</Typography>
          <Typography variant="caption" fontWeight={700}>{fmtCurr(scenario.total_at_retirement)}</Typography>
        </Box>
        {scenario.monthly_contribution > 0 && (
          <Box display="flex" justifyContent="space-between" mb={0.5}>
            <Typography variant="caption" color="text.secondary">Total Contributed</Typography>
            <Typography variant="caption" fontWeight={600}>{fmtCurr(scenario.total_contributed)}</Typography>
          </Box>
        )}
        <Box display="flex" justifyContent="space-between">
          <Typography variant="caption" color="text.secondary">Monthly Contribution</Typography>
          <Typography variant="caption" fontWeight={600}>
            {scenario.monthly_contribution === 0 ? "R0 (stopped)" : fmtCurr(scenario.monthly_contribution)}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

interface FireRowProps {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
  tooltip?: string;
}

const FireRow = ({ label, value, sub, highlight, tooltip }: FireRowProps) => (
  <Box display="flex" justifyContent="space-between" alignItems="center" py={1}
    sx={{ borderBottom: "1px solid", borderColor: "divider" }}>
    <Typography variant="body2" color={highlight ? "primary" : "text.secondary"} fontWeight={highlight ? 700 : 400}>
      {label}
      {tooltip && <InfoTip text={tooltip} />}
    </Typography>
    <Box textAlign="right">
      <Typography variant="body2" fontWeight={700} color={highlight ? "primary" : "text.primary"}>{value}</Typography>
      {sub && <Typography variant="caption" color="text.secondary">{sub}</Typography>}
    </Box>
  </Box>
);

// ─── Scenario Colour Palette ──────────────────────────────────────────────────

const SCENARIO_COLORS = ["#ef4444", "#3b82f6", "#10b981"];

// ─── Main Component ───────────────────────────────────────────────────────────

export default function RetirementPlanningPage() {
  const router = useRouter();
  const [darkMode, setDarkMode] = useState(true);
  const theme = darkMode ? brandingDarkTheme : brandingLightTheme;

  // ── Auto-population state
  const [autoInputs, setAutoInputs] = useState<AutoInputs | null>(null);
  const [loadingAuto, setLoadingAuto] = useState(false);

  // ── "Use DB value" toggles
  const [useDbValue, setUseDbValue] = useState(true);
  const [useDbIrr, setUseDbIrr] = useState(true);
  const [useDbContribution, setUseDbContribution] = useState(true);
  const [estimateLifeRate, setEstimateLifeRate] = useState(false);

  // ── Inputs: Current Situation
  const [currentValue, setCurrentValue] = useState<string>("0");
  const [currentAge, setCurrentAge] = useState<string>("35");
  const [retirementAge, setRetirementAge] = useState<string>("65");
  const [monthlyContribution, setMonthlyContribution] = useState<string>("5000");
  const [contributionAnnualIncrease, setContributionAnnualIncrease] = useState<string>("6");
  const [monthlyExpenses, setMonthlyExpenses] = useState<string>("25000");
  const [grossMonthlyIncome, setGrossMonthlyIncome] = useState<string>("50000");

  // ── Inputs: Assumptions
  const [historicalIrr, setHistoricalIrr] = useState<string>("9.5");
  const [postRetirementGrowth, setPostRetirementGrowth] = useState<string>("7");
  const [inflation, setInflation] = useState<string>("6");
  const [drawdownRate, setDrawdownRate] = useState<string>("4");
  const [lifeAnnuityRate, setLifeAnnuityRate] = useState<string>("5.5");
  const [escalation, setEscalation] = useState<string>("3");
  const [livingSplit, setLivingSplit] = useState<number>(50); // %
  const [increasedContribution, setIncreasedContribution] = useState<string>("8000");

  // ── Results
  const [result, setResult] = useState<ProjectionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabIndex, setTabIndex] = useState(0);
  const [showNominal, setShowNominal] = useState(true);
  const [snack, setSnack] = useState<{ open: boolean; msg: string; sev: "success" | "error" | "info" }>({ open: false, msg: "", sev: "info" });

  // ── Derived
  const yearsToRetirement = Math.max(1, Number(retirementAge) - Number(currentAge));
  const savingsRate = Number(grossMonthlyIncome) > 0 ? Number(monthlyContribution) / Number(grossMonthlyIncome) : 0;

  // ── Fetch auto inputs on mount
  useEffect(() => {
    async function fetchAutoInputs() {
      setLoadingAuto(true);
      try {
        const res = await axios.get("/api/retirement/auto_inputs");
        const data: AutoInputs = res.data;
        setAutoInputs(data);
        if (useDbValue) setCurrentValue(data.current_portfolio_value.toFixed(0));
        if (useDbIrr) setHistoricalIrr((data.ra_irr_historical * 100).toFixed(2));
        if (useDbContribution) setMonthlyContribution(data.avg_monthly_contribution.toFixed(0));
        setLifeAnnuityRate((data.life_annuity_rate * 100).toFixed(2));
        setInflation((data.default_inflation * 100).toFixed(1));
      } catch {
        setSnack({ open: true, msg: "Could not fetch auto inputs from DB — using defaults.", sev: "info" });
      }
      setLoadingAuto(false);
    }
    fetchAutoInputs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Re-apply DB values when toggles change
  useEffect(() => {
    if (!autoInputs) return;
    if (useDbValue) setCurrentValue(autoInputs.current_portfolio_value.toFixed(0));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useDbValue]);

  useEffect(() => {
    if (!autoInputs) return;
    if (useDbIrr) setHistoricalIrr((autoInputs.ra_irr_historical * 100).toFixed(2));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useDbIrr]);

  useEffect(() => {
    if (!autoInputs) return;
    if (useDbContribution) setMonthlyContribution(autoInputs.avg_monthly_contribution.toFixed(0));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useDbContribution]);

  // ── Calculate
  const handleCalculate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        current_ra_value: Number(currentValue),
        split_living_annuity: livingSplit / 100,
        split_life_annuity: (100 - livingSplit) / 100,
        assumed_growth: Number(postRetirementGrowth) / 100,
        drawdown_rate: Number(drawdownRate) / 100,
        inflation: Number(inflation) / 100,
        escalation: Number(escalation) / 100,
        monthly_contribution: Number(monthlyContribution),
        years_to_retirement: yearsToRetirement,
        ra_irr_historical: Number(historicalIrr) / 100,
        life_annuity_rate: Number(lifeAnnuityRate) / 100,
        monthly_expenses: Number(monthlyExpenses),
        contribution_annual_increase: Number(contributionAnnualIncrease) / 100,
        increased_monthly_contribution: Number(increasedContribution),
        database_name: "Investments",
      };
      const res = await axios.post("/api/retirement_projection", payload);
      setResult(res.data);
      setTabIndex(0);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Calculation failed. Please check your inputs.");
    }
    setLoading(false);
  }, [currentValue, livingSplit, postRetirementGrowth, drawdownRate, inflation, escalation, monthlyContribution, yearsToRetirement, historicalIrr, lifeAnnuityRate, monthlyExpenses, contributionAnnualIncrease, increasedContribution]);

  // ── Chart data: merge all scenarios onto one year axis
  const chartData = React.useMemo(() => {
    if (!result) return [];
    const maxYears = yearsToRetirement;
    return Array.from({ length: maxYears + 1 }, (_, yr) => {
      const point: Record<string, number | string> = { year: `Year ${yr}` };
      result.scenarios.forEach((s, i) => {
        const entry = s.yearly_series.find((e) => e.year === yr);
        const key = showNominal ? "portfolio_value" : "portfolio_value_real";
        point[`scenario_${i}`] = entry ? entry[key] : 0;
      });
      if (result.fire_metrics && Object.keys(result.fire_metrics).length > 0) {
        point.fire_line = showNominal
          ? result.fire_metrics.fire_number_at_retirement
          : result.fire_metrics.fire_number_today;
      }
      return point;
    });
  }, [result, yearsToRetirement, showNominal]);



  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ backgroundColor: "background.default", minHeight: "100vh", pb: 8 }}>
        {/* ── Header ── */}
        <Box sx={{
          background: darkMode
            ? "linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)"
            : "linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)",
          borderBottom: "1px solid",
          borderColor: "divider",
          px: 3,
          py: 2,
          mb: 4,
          position: "sticky",
          top: 0,
          zIndex: 100,
          backdropFilter: "blur(12px)",
        }}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box display="flex" alignItems="center" gap={2}>
              <DrawerComponent />
              <IconButton onClick={() => router.back()} color="inherit">
                <KeyboardBackspaceIcon />
              </IconButton>
              <Box>
                <Typography variant="h5" fontWeight={800} sx={{
                  background: "linear-gradient(90deg, #3b82f6, #10b981, #f59e0b)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}>
                  Retirement & FIRE Calculator
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Plan your retirement · Living & Life Annuity · Financial Independence
                </Typography>
              </Box>
            </Box>
            <Box display="flex" alignItems="center" gap={1}>
              {loadingAuto && <CircularProgress size={18} />}
              <Chip icon={<AutoFixHighIcon />} label={`${yearsToRetirement} yrs to retirement`} color="primary" variant="outlined" size="small" />
              <Chip label={`Savings rate: ${pct(savingsRate)}`} color={savingsRate >= 0.15 ? "success" : "warning"} size="small" />
              <IconButton onClick={() => setDarkMode((p) => !p)} color="inherit">
                {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
              </IconButton>
            </Box>
          </Box>
        </Box>

        <Container maxWidth="xl">
          <Grid container spacing={3}>
            {/* ──────────────── LEFT PANEL: Inputs ──────────────── */}
            <Grid size={{ xs: 12, lg: 3 }}>
              <Box sx={{ position: "sticky", top: 80 }}>
                {/* Current Situation */}
                <Paper elevation={3} sx={{ p: 2.5, borderRadius: 3, mb: 2, background: darkMode ? "rgba(30,41,59,0.8)" : "background.paper" }}>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <AccountBalanceIcon color="primary" />
                    <Typography variant="subtitle1" fontWeight={700}>Current Situation</Typography>
                  </Box>

                  <AutoField
                    label="Current Portfolio Value (ZAR)"
                    value={currentValue}
                    onChange={setCurrentValue}
                    useAuto={useDbValue}
                    setUseAuto={setUseDbValue}
                    unit="ZAR"
                    tooltip="Your total RA / investment portfolio value. Auto-fetched from your investment database."
                  />
                  <Grid container spacing={1}>
                    <Grid size={{ xs: 6 }}>
                      <AutoField label="Current Age" value={currentAge} onChange={setCurrentAge} unit="years" />
                    </Grid>
                    <Grid size={{ xs: 6 }}>
                      <AutoField label="Retirement Age" value={retirementAge} onChange={setRetirementAge} unit="years" />
                    </Grid>
                  </Grid>

                  <Box mb={2} p={1.5} sx={{ background: "primary.main", borderRadius: 2, bgcolor: darkMode ? "rgba(59,130,246,0.1)" : "rgba(59,130,246,0.05)", border: "1px solid", borderColor: "primary.main", opacity: 0.9 }}>
                    <Typography variant="caption" color="primary" fontWeight={700}>
                      Years to Retirement: {yearsToRetirement}
                    </Typography>
                  </Box>

                  <AutoField
                    label="Monthly Contribution"
                    value={monthlyContribution}
                    onChange={setMonthlyContribution}
                    useAuto={useDbContribution}
                    setUseAuto={setUseDbContribution}
                    unit="ZAR"
                    tooltip="Current monthly RA/investment contribution. Auto-calculated from your last 12 months of data."
                  />
                  <AutoField
                    label="Increased Monthly Contribution"
                    value={increasedContribution}
                    onChange={setIncreasedContribution}
                    unit="ZAR"
                    tooltip="The higher contribution amount for Scenario 3."
                  />
                  <AutoField
                    label="Contribution Annual Increase"
                    value={contributionAnnualIncrease}
                    onChange={setContributionAnnualIncrease}
                    unit="%"
                    tooltip="By how much you increase your contribution each year (e.g. 6% = CPI-linked)."
                  />
                  <AutoField
                    label="Monthly Living Expenses (today)"
                    value={monthlyExpenses}
                    onChange={setMonthlyExpenses}
                    unit="ZAR"
                    tooltip="Your current monthly expenses. Used to calculate your FIRE number (25 × annual expenses)."
                  />
                  <AutoField
                    label="Gross Monthly Income"
                    value={grossMonthlyIncome}
                    onChange={setGrossMonthlyIncome}
                    unit="ZAR"
                    tooltip="Used to calculate your savings rate: contributions ÷ gross income."
                  />
                </Paper>

                {/* Assumptions */}
                <Paper elevation={3} sx={{ p: 2.5, borderRadius: 3, mb: 2, background: darkMode ? "rgba(30,41,59,0.8)" : "background.paper" }}>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <TrendingUpIcon color="secondary" />
                    <Typography variant="subtitle1" fontWeight={700}>Assumptions</Typography>
                  </Box>

                  <AutoField
                    label="Historical RA IRR (pre-retirement growth)"
                    value={historicalIrr}
                    onChange={setHistoricalIrr}
                    useAuto={useDbIrr}
                    setUseAuto={setUseDbIrr}
                    unit="%"
                    tooltip="Used as the growth rate until retirement. Auto-calculated from your portfolio's Internal Rate of Return."
                  />
                  <AutoField
                    label="Post-Retirement Growth (Living Annuity)"
                    value={postRetirementGrowth}
                    onChange={setPostRetirementGrowth}
                    unit="%"
                    tooltip="Expected investment growth rate for your Living Annuity after retirement."
                  />
                  <AutoField
                    label="Inflation Rate"
                    value={inflation}
                    onChange={setInflation}
                    unit="%"
                    tooltip="Expected annual inflation. Used to calculate real (inflation-adjusted) income."
                  />
                  <AutoField
                    label="Life Annuity Purchase Rate"
                    value={lifeAnnuityRate}
                    onChange={setLifeAnnuityRate}
                    useAuto={estimateLifeRate}
                    setUseAuto={setEstimateLifeRate}
                    unit="%"
                    tooltip="The annual rate at which an insurer converts your capital to income. Default 5.5%. Toggle 'Auto' to try fetching the current market rate."
                  />
                  <AutoField
                    label="CPI Escalation (Life Annuity)"
                    value={escalation}
                    onChange={setEscalation}
                    unit="%"
                    tooltip="Annual income escalation for your Life Annuity — 0% = level, CPI = inflation-linked."
                  />

                  {/* Drawdown Rate Slider */}
                  <Box mb={2}>
                    <Box display="flex" justifyContent="space-between" mb={0.5}>
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        Living Annuity Drawdown Rate
                        <InfoTip text="FSCA regulated: 2.5%–17.5% per year. 4% is widely considered sustainable." />
                      </Typography>
                      <Chip label={`${drawdownRate}%`} size="small" color={Number(drawdownRate) <= 6 ? "success" : Number(drawdownRate) <= 10 ? "warning" : "error"} />
                    </Box>
                    <Slider
                      value={Number(drawdownRate)}
                      onChange={(_, v) => setDrawdownRate(String(v))}
                      min={2.5} max={17.5} step={0.5}
                      marks={[{ value: 2.5, label: "2.5%" }, { value: 4, label: "4%" }, { value: 10, label: "10%" }, { value: 17.5, label: "17.5%" }]}
                      color={Number(drawdownRate) <= 6 ? "primary" : Number(drawdownRate) <= 10 ? "warning" : "error"}
                    />
                  </Box>

                  {/* Living/Life Split Slider */}
                  <Box mb={2}>
                    <Box display="flex" justifyContent="space-between" mb={0.5}>
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        Annuity Split
                        <InfoTip text="Split of your capital between Living Annuity (flexible, you own it) and Life Annuity (guaranteed income for life)." />
                      </Typography>
                      <Box>
                        <Chip label={`Living ${livingSplit}%`} size="small" color="primary" sx={{ mr: 0.5 }} />
                        <Chip label={`Life ${100 - livingSplit}%`} size="small" color="secondary" />
                      </Box>
                    </Box>
                    <Slider
                      value={livingSplit}
                      onChange={(_, v) => setLivingSplit(v as number)}
                      min={0} max={100} step={5}
                      marks={[{ value: 0, label: "0%" }, { value: 50, label: "50/50" }, { value: 100, label: "100%" }]}
                    />
                  </Box>
                </Paper>

                {/* Calculate Button */}
                <Button
                  fullWidth
                  variant="contained"
                  size="large"
                  onClick={handleCalculate}
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <CalculateIcon />}
                  sx={{
                    py: 1.8,
                    borderRadius: 3,
                    fontWeight: 800,
                    fontSize: "1rem",
                    background: "linear-gradient(135deg, #3b82f6, #10b981)",
                    boxShadow: "0 4px 20px rgba(59,130,246,0.4)",
                    "&:hover": { boxShadow: "0 6px 28px rgba(59,130,246,0.6)" },
                  }}
                >
                  {loading ? "Calculating..." : "Calculate Projections"}
                </Button>
              </Box>
            </Grid>

            {/* ──────────────── RIGHT PANEL: Results ──────────────── */}
            <Grid size={{ xs: 12, lg: 9 }}>
              {error && (
                <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              {!result ? (
                <Paper elevation={0} sx={{
                  height: 500, display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center",
                  border: "2px dashed", borderColor: "divider", borderRadius: 4,
                  gap: 2,
                }}>
                  <CalculateIcon sx={{ fontSize: 64, opacity: 0.2 }} />
                  <Typography variant="h6" color="text.secondary">
                    Fill in your details and click Calculate Projections
                  </Typography>
                  <Typography variant="body2" color="text.secondary" textAlign="center" maxWidth={400}>
                    We&apos;ll project your retirement income across 3 scenarios, show your FIRE number,
                    and give you a year-by-year growth chart.
                  </Typography>
                </Paper>
              ) : (
                <>
                  {/* ── Tabs ── */}
                  <Paper elevation={0} sx={{ mb: 3, borderRadius: 3, overflow: "hidden", border: "1px solid", borderColor: "divider" }}>
                    <Tabs
                      value={tabIndex}
                      onChange={(_, v) => setTabIndex(v)}
                      variant="scrollable"
                      scrollButtons="auto"
                      sx={{ borderBottom: "1px solid", borderColor: "divider", px: 2 }}
                    >
                      <Tab label="📊 Scenarios" />
                      <Tab label="🔥 FIRE Metrics" />
                      <Tab label="📈 Growth Chart" />
                      <Tab label="🧮 Calculation Details" />
                    </Tabs>

                    {/* ── Tab 0: Scenarios ── */}
                    {tabIndex === 0 && (
                      <Box p={3}>
                        <Grid container spacing={2.5}>
                          {result.scenarios.map((s, i) => (
                            <Grid size={{ xs: 12, md: 4 }} key={i}>
                              <ScenarioCard scenario={s} idx={i} darkMode={darkMode} livingSplit={livingSplit} />
                            </Grid>
                          ))}
                        </Grid>

                        {/* Income comparison bar */}
                        <Paper elevation={0} sx={{ mt: 3, p: 2, borderRadius: 3, background: darkMode ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)", border: "1px solid", borderColor: "divider" }}>
                          <Typography variant="subtitle2" fontWeight={700} mb={1.5}>Monthly Income Comparison</Typography>
                          {result.scenarios.map((s, i) => {
                            const maxIncome = Math.max(...result.scenarios.map((x) => x.total_monthly_income));
                            const pctWidth = maxIncome > 0 ? (s.total_monthly_income / maxIncome) * 100 : 0;
                            return (
                              <Box key={i} mb={1.5}>
                                <Box display="flex" justifyContent="space-between" mb={0.3}>
                                  <Typography variant="caption" color="text.secondary">{s.label}</Typography>
                                  <Typography variant="caption" fontWeight={700} color={SCENARIO_COLORS[i]}>
                                    {fmtCurr(s.total_monthly_income)}/mo (real: {fmtCurr(s.total_monthly_income_real)})
                                  </Typography>
                                </Box>
                                <LinearProgress
                                  variant="determinate"
                                  value={pctWidth}
                                  sx={{ height: 10, borderRadius: 5, bgcolor: "divider", "& .MuiLinearProgress-bar": { backgroundColor: SCENARIO_COLORS[i], borderRadius: 5 } }}
                                />
                              </Box>
                            );
                          })}
                        </Paper>

                        {/* Living expense coverage */}
                        {Number(monthlyExpenses) > 0 && (
                          <Paper elevation={0} sx={{ mt: 2, p: 2, borderRadius: 3, background: darkMode ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)", border: "1px solid", borderColor: "divider" }}>
                            <Typography variant="subtitle2" fontWeight={700} mb={1.5}>
                              Expense Coverage
                              <InfoTip text="How much of your inflation-adjusted monthly expenses will be covered by each scenario." />
                            </Typography>
                            {result.scenarios.map((s, i) => {
                              const inflatedExpenses = Number(monthlyExpenses) * Math.pow(1 + Number(inflation) / 100, yearsToRetirement);
                              const coverage = inflatedExpenses > 0 ? (s.total_monthly_income / inflatedExpenses) * 100 : 0;
                              return (
                                <Box key={i} mb={1}>
                                  <Box display="flex" justifyContent="space-between" mb={0.3}>
                                    <Typography variant="caption" color="text.secondary">{s.label}</Typography>
                                    <Chip
                                      label={`${coverage.toFixed(0)}% of expenses covered`}
                                      size="small"
                                      color={coverage >= 100 ? "success" : coverage >= 75 ? "warning" : "error"}
                                    />
                                  </Box>
                                  <LinearProgress
                                    variant="determinate"
                                    value={Math.min(100, coverage)}
                                    sx={{ height: 8, borderRadius: 5, bgcolor: "divider", "& .MuiLinearProgress-bar": { backgroundColor: coverage >= 100 ? "#10b981" : coverage >= 75 ? "#f59e0b" : "#ef4444", borderRadius: 5 } }}
                                  />
                                </Box>
                              );
                            })}
                            <Typography variant="caption" color="text.secondary" mt={1} display="block">
                              * Inflation-adjusted monthly expenses at retirement: {fmtCurr(Number(monthlyExpenses) * Math.pow(1 + Number(inflation) / 100, yearsToRetirement))}
                            </Typography>
                          </Paper>
                        )}
                      </Box>
                    )}

                    {/* ── Tab 1: FIRE Metrics ── */}
                    {tabIndex === 1 && (
                      <Box p={3}>
                        {Object.keys(result.fire_metrics).length === 0 ? (
                          <Alert severity="info" sx={{ borderRadius: 2 }}>
                            Enter your monthly living expenses to see FIRE metrics.
                          </Alert>
                        ) : (
                          <Grid container spacing={3}>
                            {/* On Track indicator */}
                            <Grid size={{ xs: 12 }}>
                              <Paper elevation={0} sx={{
                                p: 3, borderRadius: 3, textAlign: "center",
                                background: result.fire_metrics.is_on_track
                                  ? "linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05))"
                                  : "linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05))",
                                border: "2px solid",
                                borderColor: result.fire_metrics.is_on_track ? "#10b981" : "#ef4444",
                              }}>
                                <LocalFireDepartmentIcon sx={{ fontSize: 48, color: result.fire_metrics.is_on_track ? "#10b981" : "#ef4444", mb: 1 }} />
                                <Typography variant="h5" fontWeight={800} color={result.fire_metrics.is_on_track ? "#10b981" : "#ef4444"}>
                                  {result.fire_metrics.is_on_track ? "🎉 You're On Track for FIRE!" : "⚠️ Not Yet On Track for FIRE"}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" mt={0.5}>
                                  {result.fire_metrics.is_on_track
                                    ? "Your projected portfolio at retirement exceeds your FIRE number."
                                    : `You need ${fmtCurr(result.fire_metrics.extra_monthly_needed)}/mo extra to reach your FIRE number.`}
                                </Typography>
                              </Paper>
                            </Grid>

                            {/* FIRE number cards */}
                            <Grid size={{ xs: 12, sm: 4 }}>
                              <Card variant="outlined" sx={{ borderRadius: 3, textAlign: "center", p: 2, borderColor: "#f59e0b" }}>
                                <Typography variant="caption" color="text.secondary">Lean FIRE</Typography>
                                <Typography variant="h6" fontWeight={800} color="#f59e0b">{fmtCurr(result.fire_metrics.lean_fire_today)}</Typography>
                                <Typography variant="caption" color="text.secondary">today / {fmtCurr(result.fire_metrics.lean_fire_at_retirement)} at retirement</Typography>
                                <Typography variant="caption" display="block" color="text.secondary" mt={0.5}>5% withdrawal · 20× expenses</Typography>
                              </Card>
                            </Grid>
                            <Grid size={{ xs: 12, sm: 4 }}>
                              <Card variant="outlined" sx={{ borderRadius: 3, textAlign: "center", p: 2, borderColor: "#3b82f6" }}>
                                <Typography variant="caption" color="text.secondary">FIRE (4% Rule)</Typography>
                                <Typography variant="h6" fontWeight={800} color="#3b82f6">{fmtCurr(result.fire_metrics.fire_number_today)}</Typography>
                                <Typography variant="caption" color="text.secondary">today / {fmtCurr(result.fire_metrics.fire_number_at_retirement)} at retirement</Typography>
                                <Typography variant="caption" display="block" color="text.secondary" mt={0.5}>4% withdrawal · 25× expenses</Typography>
                              </Card>
                            </Grid>
                            <Grid size={{ xs: 12, sm: 4 }}>
                              <Card variant="outlined" sx={{ borderRadius: 3, textAlign: "center", p: 2, borderColor: "#10b981" }}>
                                <Typography variant="caption" color="text.secondary">Fat FIRE</Typography>
                                <Typography variant="h6" fontWeight={800} color="#10b981">{fmtCurr(result.fire_metrics.fat_fire_today)}</Typography>
                                <Typography variant="caption" color="text.secondary">today / {fmtCurr(result.fire_metrics.fat_fire_at_retirement)} at retirement</Typography>
                                <Typography variant="caption" display="block" color="text.secondary" mt={0.5}>3% withdrawal · 33× expenses</Typography>
                              </Card>
                            </Grid>

                            {/* Detailed metrics */}
                            <Grid size={{ xs: 12, md: 6 }}>
                              <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
                                <Typography variant="subtitle2" fontWeight={700} mb={1}>Progress Metrics</Typography>
                                <FireRow
                                  label="Current Portfolio Value"
                                  value={fmtCurr(result.fire_metrics.current_value)}
                                  tooltip="Your current total investment value"
                                />
                                <FireRow
                                  label="Coast FIRE Number (today)"
                                  value={fmtCurr(result.fire_metrics.coast_fire_today)}
                                  tooltip="If you have this amount now and stop contributing, it will grow to your FIRE number by retirement. Formula: FIRE Number at Retirement ÷ (1 + growth)^years"
                                />
                                <FireRow
                                  label="Projected at Retirement"
                                  value={fmtCurr(result.fire_metrics.projected_at_retirement)}
                                  highlight
                                  tooltip="Projected portfolio value at retirement (continuing current contributions)"
                                />
                                <FireRow
                                  label="Shortfall"
                                  value={result.fire_metrics.shortfall > 0 ? fmtCurr(result.fire_metrics.shortfall) : "None 🎉"}
                                  tooltip="FIRE Number at retirement minus projected portfolio"
                                />
                                <FireRow
                                  label="Extra Monthly Needed"
                                  value={result.fire_metrics.extra_monthly_needed > 0 ? `${fmtCurr(result.fire_metrics.extra_monthly_needed)}/mo` : "None needed 🎉"}
                                  tooltip="Additional monthly contribution required to bridge the shortfall"
                                />
                              </Paper>
                            </Grid>
                            <Grid size={{ xs: 12, md: 6 }}>
                              <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
                                <Typography variant="subtitle2" fontWeight={700} mb={1}>Timeline Metrics</Typography>
                                <FireRow
                                  label="Monthly Living Expenses (today)"
                                  value={fmtCurr(result.fire_metrics.annual_expenses_today / 12)}
                                />
                                <FireRow
                                  label="Annual Expenses (today)"
                                  value={fmtCurr(result.fire_metrics.annual_expenses_today)}
                                />
                                <FireRow
                                  label="Months to FIRE (at current rate)"
                                  value={result.fire_metrics.months_to_fire != null ? `${result.fire_metrics.months_to_fire} months (${(result.fire_metrics.months_to_fire / 12).toFixed(1)} yrs)` : "Not reachable at current rate"}
                                  tooltip="How many months until your portfolio hits the FIRE number, assuming you continue contributing"
                                />
                                <FireRow
                                  label="Current Savings Rate"
                                  value={pct(savingsRate)}
                                  sub={savingsRate >= 0.15 ? "✅ Good (≥15%)" : savingsRate >= 0.1 ? "⚠️ Moderate" : "❌ Below 10%"}
                                  tooltip="Monthly contribution ÷ gross monthly income"
                                />
                                <FireRow
                                  label="Years to Retirement"
                                  value={`${yearsToRetirement} years`}
                                />
                              </Paper>
                            </Grid>
                          </Grid>
                        )}
                      </Box>
                    )}

                    {/* ── Tab 2: Chart ── */}
                    {tabIndex === 2 && (
                      <Box p={3}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                          <Typography variant="subtitle1" fontWeight={700}>Portfolio Growth Projection</Typography>
                          <FormControlLabel
                            control={<Switch checked={showNominal} onChange={(e) => setShowNominal(e.target.checked)} />}
                            label={<Typography variant="caption">{showNominal ? "Nominal" : "Real (inflation-adjusted)"}</Typography>}
                          />
                        </Box>
                        <ResponsiveContainer width="100%" height={450}>
                          <AreaChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
                            <defs>
                              {result.scenarios.map((_, i) => (
                                <linearGradient key={i} id={`grad${i}`} x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor={SCENARIO_COLORS[i]} stopOpacity={0.3} />
                                  <stop offset="95%" stopColor={SCENARIO_COLORS[i]} stopOpacity={0.02} />
                                </linearGradient>
                              ))}
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke={darkMode ? "#334155" : "#e2e8f0"} />
                            <XAxis dataKey="year" tick={{ fontSize: 11, fill: darkMode ? "#94a3b8" : "#64748b" }} interval={Math.max(1, Math.floor(yearsToRetirement / 8))} />
                            <YAxis
                              tick={{ fontSize: 11, fill: darkMode ? "#94a3b8" : "#64748b" }}
                              tickFormatter={(v) => `R${(v / 1_000_000).toFixed(1)}M`}
                            />
                            <ReTooltip
                              contentStyle={{
                                backgroundColor: darkMode ? "#1e293b" : "#fff",
                                border: `1px solid ${darkMode ? "#334155" : "#e2e8f0"}`,
                                borderRadius: 8,
                              }}
                              formatter={(value: number, name: string) => {
                                const idx = Number(name.split("_")[1]);
                                const label = result.scenarios[idx]?.label || name;
                                return [fmtCurr(value), label];
                              }}
                            />
                            <Legend formatter={(value) => {
                              const idx = Number(value.split("_")[1]);
                              return result.scenarios[idx]?.label || value;
                            }} />
                            {result.scenarios.map((_, i) => (
                              <Area
                                key={i}
                                type="monotone"
                                dataKey={`scenario_${i}`}
                                stroke={SCENARIO_COLORS[i]}
                                fill={`url(#grad${i})`}
                                strokeWidth={2.5}
                                dot={false}
                              />
                            ))}
                            {chartData[0]?.fire_line && (
                              <ReferenceLine
                                y={chartData[0].fire_line as number}
                                stroke="#f59e0b"
                                strokeDasharray="8 4"
                                strokeWidth={2}
                                label={{ value: "FIRE 🔥", position: "right", fill: "#f59e0b", fontSize: 12 }}
                              />
                            )}
                          </AreaChart>
                        </ResponsiveContainer>
                        <Typography variant="caption" color="text.secondary" display="block" textAlign="center" mt={1}>
                          Dashed orange line = FIRE Number · {showNominal ? "Nominal" : "Real (today's money)"} values
                        </Typography>
                      </Box>
                    )}

                    {/* ── Tab 3: Calculation Details ── */}
                    {tabIndex === 3 && (
                      <Box p={3}>
                        <Typography variant="subtitle1" fontWeight={700} mb={2}>📐 Inputs Used for Calculation</Typography>
                        <Paper elevation={0} sx={{ p: 2, borderRadius: 2, border: "1px solid", borderColor: "divider", mb: 3 }}>
                          <Grid container spacing={1}>
                            {Object.entries(result.calculation_inputs).map(([key, val]) => (
                              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={key}>
                                <Box display="flex" justifyContent="space-between" py={0.75} sx={{ borderBottom: "1px solid", borderColor: "divider" }}>
                                  <Typography variant="caption" color="text.secondary">
                                    {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                                  </Typography>
                                  <Typography variant="caption" fontWeight={700}>
                                    {typeof val === "number" ? (String(val).includes(".") && val < 1000 ? `${val}` : fmt(Number(val))) : String(val)}
                                  </Typography>
                                </Box>
                              </Grid>
                            ))}
                          </Grid>
                        </Paper>

                        <Typography variant="subtitle1" fontWeight={700} mb={2}>📖 Formulas Used</Typography>
                        {Object.entries(result.formulas).map(([key, formula]) => (
                          <Accordion key={key} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, mb: 1, "&:before": { display: "none" } }}>
                            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                              <Typography variant="body2" fontWeight={600}>
                                {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                              </Typography>
                            </AccordionSummary>
                            <AccordionDetails>
                              <Typography variant="body2" color="text.secondary" fontFamily="monospace" sx={{
                                bgcolor: darkMode ? "rgba(0,0,0,0.3)" : "rgba(0,0,0,0.04)",
                                p: 1.5, borderRadius: 1
                              }}>
                                {formula}
                              </Typography>
                            </AccordionDetails>
                          </Accordion>
                        ))}

                        <Alert severity="info" sx={{ mt: 3, borderRadius: 2 }}>
                          <Typography variant="caption">
                            <strong>Disclaimer:</strong> These projections are estimates for planning purposes only.
                            Actual investment returns, inflation, and annuity rates will vary. Consult a qualified financial
                            advisor before making retirement decisions. Life annuity income estimates use a simplified purchase
                            rate proxy — get a formal quote from an insurer for accurate figures.
                          </Typography>
                        </Alert>
                      </Box>
                    )}
                  </Paper>
                </>
              )}
            </Grid>
          </Grid>
        </Container>

        <Snackbar
          open={snack.open}
          autoHideDuration={5000}
          onClose={() => setSnack((p) => ({ ...p, open: false }))}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        >
          <Alert severity={snack.sev} onClose={() => setSnack((p) => ({ ...p, open: false }))} sx={{ width: "100%" }}>
            {snack.msg}
          </Alert>
        </Snackbar>
      </Box>
    </ThemeProvider>
  );
}
