"use client";
import { Container, Grid, IconButton, Paper } from '@mui/material';
import axios from 'axios';
import { useEffect, useState } from 'react';
import LineGraph from '../Charts/Graphs/LineGraph';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { ThemeProvider } from '@mui/material/styles';
import StickyHeadTable from '../Charts/Tables/StickyHeadTable';
import PieChart from '../Charts/Graphs/PieChart';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import CircularProgress from '@mui/material/CircularProgress';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';

interface Point {
  x: Date;
  y: number;
};

interface LineGraphData {
  label: string;
  data: Point[];
  borderColour: string;
};

interface PieChartData {
  labels: string[];
  datasets: {
    data: number[];
    backgroundColor: string[];
  }[];
}

interface InvestmentSummaryInterface {
  id: number;
  institution_name: string;
  investment_name: string;
  investment_type: string;
  unit_currency: string;
  investment_value: number;
  unit_price: number;
  total_units_held: number;
  initial_unit_price: number;
  initial_investment_date: string;
  exchange_rate?: number;
  investment_value_in_native_currency?: number;
  unit_price_in_native_currency?: number;
  initial_unit_price_in_native_currency?: number;
}

interface AllInvestmentData {
  id: number;
  investment_name: string;
  unit_price_date: any;
  unit_price: number;
  number_of_units: number;
  investment_value: number;
  unit_currency: string;
  investment_type: string;
  exchange_rate: number;
  investment_value_in_native_currency: number;

};

interface InvestmentTypeTableRowsInterface {
  id: number; 
  investment_type: string;
  investment_value_in_native_currency: number;
  initial_investment_date: string;
};

interface InvestmentCurrencyTableRowsInterface {
  id: number;
  unit_currency: string;
  investment_value_in_native_currency: number;
  initial_investment_date: string;
};

interface InvestmentInstitutionTableRowsInterface {
  id: number;
  institution_name: string;
  investment_value_in_native_currency: number;
  initial_investment_date: string;
};

interface MenuItem {
  heading: string;
  items: string[];
  urls: string[];
}

const investment_summary_table_columns = [
  { id: 'investment_name', label: 'Investment Name', minWidth: 170 },
  { id: 'investment_type', label: 'Investment Type', minWidth: 100 },
  //{ id: 'unit_currency', label: 'Unit Currency', minWidth: 100 },
  //{id: "exchange_rate", label: "Exchange Rate", minWidth: 170},
  { id: "investment_value_in_native_currency", label: "Investment Value in R", minWidth: 100},
  { id: "unit_price_in_native_currency", label: "Unit Price in R", minWidth: 100},
  { id: 'total_units_held', label: 'Total Units Held', minWidth: 100 },
  { id: "initial_unit_price_in_native_currency", label: "Initial Unit Price in R", minWidth: 100},
  { id: "initial_investment_date", label: "Initial Investment Date", minWidth: 100},
];

const investment_type_table_columns =[
  {id: "investment_type", label: "Investment Type", minWidth: 50},
  {id: "investment_value_in_native_currency", label: "Investment Value in R", minWidth: 50},
  {id: "initial_investment_date", label: "Initial Investment Date", minWidth: 50}
];

const investment_currency_table_columns =[
  {id: "unit_currency", label: "Investment Currency", minWidth: 50},
  {id: "investment_value_in_native_currency", label: "Investment Value in R", minWidth: 50},
  {id: "initial_investment_date", label: "Initial Investment Date", minWidth: 50}
];

const investment_institution_table_columns =[
  {id: "institution_name", label: "Institution's Name", minWidth: 50},
  {id: "investment_value_in_native_currency", label: "Investment Value in R", minWidth: 50},
  {id: "initial_investment_date", label: "Initial Investment Date", minWidth: 50}
];

const getRandomColor = () => {
  const letters = '0123456789ABCDEF';
  let color = '#';
  for (let i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
};


function AllInvestments() {
  const [AllInvestmentValues, setAllInvestmentValues] = useState<LineGraphData[] | null>(null);
  const [AllInvestmentPieValues, setAllInvestmentPieValues] = useState<PieChartData | null>(null);
  const [InvestmentSummary, setInvestmentSummary] = useState<InvestmentSummaryInterface[] | null>(null);
  const [InvestmentTypePieValues, setInvestmentTypePieValues] = useState<PieChartData | null>(null);
  const [InvestmentTypeTableRows, setInvestmentTypeTableRows] = useState<InvestmentTypeTableRowsInterface[] | null>(null);
  const [InvestmentCurrencyPieValues, setInvestmentCurrencyPieValues] = useState<PieChartData | null>(null);
  const [InvestmentCurrencyTableRows, setInvestmentCurrencyTableRows] = useState<InvestmentCurrencyTableRowsInterface[] | null>(null);
  const [InvestmentInsitutionPieValues, setInvestmentInstitutionPieValues] = useState<PieChartData | null>(null);
  const [InvestmentInsitutionTableRows, setInvestmentInstitutionTableRows] = useState<InvestmentInstitutionTableRowsInterface[] | null>(null);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [minDate, setMinDate] = useState<Date>();
  const [maxDate, setMaxDate] = useState<Date>();
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    async function fetchAllInvestmentValues() {
      try {
        const InvestmentSummaryResponse = await axios.get("http://127.0.0.1:3337/investment_summary/Investments")
        const InvestmentSummary: InvestmentSummaryInterface[] = InvestmentSummaryResponse.data;

        const investment_values_response = await axios.get("http://127.0.0.1:3337/all_investment_values/Investments");
        const data: AllInvestmentData[] = investment_values_response.data;     
        console.log(data)
        const InvestmentNames: Array<string> = InvestmentSummary.map((investment) => investment.investment_name)
        const AllInvestmentGraphData: LineGraphData[] = []
         InvestmentNames.forEach((investment) =>{
          let tempAllInvestmentData = data.filter((item) => item.investment_name == investment)
                    let mappedData = tempAllInvestmentData.map((item) => ({
            x: new Date(item.unit_price_date),
            y: item.investment_value_in_native_currency
          }));

          let tempInvestmentData: LineGraphData = {
            label: investment,
            data: mappedData,
            borderColour: getRandomColor()
          };
          AllInvestmentGraphData.push(tempInvestmentData)

        });

        const labels: string[] = [];
        const values: number[] = [];
        const backgroundColors: string[] = [];

        const lastValues: { [key: string]: { investment_value_in_native_currency?: number, exchange_rate?: number } } = {};

        data.forEach((item) => {
          lastValues[item.investment_name] = {
            investment_value_in_native_currency: item.investment_value_in_native_currency,
            exchange_rate: item.exchange_rate,
          };
        });

        InvestmentSummary.forEach((investment) => {
          labels.push(investment.investment_name);

          const lastValue = lastValues[investment.investment_name];
          if (lastValue !== undefined && lastValue.exchange_rate !== undefined) {
            const unitPriceInNativeCurrency = investment.unit_price * lastValue.exchange_rate;
            const initialUnitPriceInNativeCurrency = investment.initial_unit_price * lastValue.exchange_rate;
            const totalUnitsHeld = investment.total_units_held;
            investment.investment_value_in_native_currency = unitPriceInNativeCurrency * totalUnitsHeld;
            investment.unit_price_in_native_currency = unitPriceInNativeCurrency;
            investment.initial_unit_price_in_native_currency = initialUnitPriceInNativeCurrency;
            investment.initial_investment_date = String(new Date(investment.initial_investment_date).toLocaleDateString('en-ZA', { day: '2-digit', month: '2-digit', year: 'numeric' }))

            values.push(investment.investment_value_in_native_currency ?? 0);
            backgroundColors.push(getRandomColor());
          }
        });
        
        const totalInvestmentValue = values.reduce((total, value) => total + value, 0);

        const pieChartData: PieChartData = {
          labels: labels,
          datasets: [{
            data: values.map(value => (value/totalInvestmentValue)*100),
            backgroundColor: backgroundColors,
          }]
        };

        const investmentTypeGroups = InvestmentSummary.reduce((groups: { [key: string]: { totalValue: number, minDate: Date } }, investment) => {
          if (!groups[investment.investment_type]) {
            groups[investment.investment_type] = {
              totalValue: 0,
              minDate: new Date(),
            };
          }
          groups[investment.investment_type].totalValue += investment.investment_value_in_native_currency ?? 0;
        
          if (investment.initial_investment_date && new Date(investment.initial_investment_date) < groups[investment.investment_type].minDate) {
            groups[investment.investment_type].minDate = new Date(investment.initial_investment_date);
          }
        
          return groups;
        }, {});
        
        const investmentTypeLabels = Object.keys(investmentTypeGroups);
        const investmentTypeValues = Object.values(investmentTypeGroups).map(group => group.totalValue);
        const investmentTypeMinDates = Object.values(investmentTypeGroups).map(group => group.minDate);
        const totalTypeInvestmentValue = investmentTypeValues.reduce((total, value) => total + value, 0);
        
        const investmentTypePieChartData: PieChartData = {
          labels: investmentTypeLabels,
          datasets: [{
            data: investmentTypeValues.map( value => (value/totalTypeInvestmentValue)*100),
            backgroundColor: investmentTypeLabels.map(() => getRandomColor()),
          }],
        };
      
        const investmentTypeTableRows = Object.entries(investmentTypeGroups).map(([investmentType, { totalValue, minDate }], index) => ({
          id: index,
          investment_type: investmentType,
          investment_value_in_native_currency: totalValue,
          initial_investment_date: minDate.toLocaleDateString('en-ZA', { day: '2-digit', month: '2-digit', year: 'numeric' }),
        }));
        
        const currencyGroups = InvestmentSummary.reduce((groups: { [key: string]: { totalValue: number, minDate: Date } }, investment) => {
          if (!groups[investment.unit_currency]) {
            groups[investment.unit_currency] = {
              totalValue: 0,
              minDate: new Date(),
            };
          }
          groups[investment.unit_currency].totalValue += investment.investment_value_in_native_currency ?? 0;
        
          // Check if the current investment date is earlier than the stored minimum date
          if (investment.initial_investment_date && new Date(investment.initial_investment_date) < groups[investment.unit_currency].minDate) {
            groups[investment.unit_currency].minDate = new Date(investment.initial_investment_date);
          }
        
          return groups;
        }, {});
        
        const currencyLabels = Object.keys(currencyGroups);
        const currencyValues = Object.values(currencyGroups).map(group => group.totalValue);
        const currencyMinDates = Object.values(currencyGroups).map(group => group.minDate);
        const totalCurrencyInvestmentValue = currencyValues.reduce((total, value) => total + value, 0);
        
        const currencyPieChartData: PieChartData = {
          labels: currencyLabels,
          datasets: [{
            data: currencyValues.map( value => (value/totalCurrencyInvestmentValue)*100),
            backgroundColor: currencyLabels.map(() => getRandomColor()),
          }],
        };
        
        const currencyTableRows = Object.entries(currencyGroups).map(([currency, { totalValue, minDate }], index) => ({
          id: index,
          unit_currency: currency,
          investment_value_in_native_currency: totalValue,
          initial_investment_date: minDate.toLocaleDateString('en-ZA', { day: '2-digit', month: '2-digit', year: 'numeric' }),
        }));
        
        // Filter out invalid dates
        const times = data
          .map(item => new Date(item.unit_price_date).getTime())
          .filter(time => !isNaN(time));
        
        let min: Date | undefined;
        let max: Date | undefined;
        
        if (times.length > 0) {
          const minTime = times.reduce((a, b) => Math.min(a, b), Infinity);
          const maxTime = times.reduce((a, b) => Math.max(a, b), -Infinity);
        
          min = new Date(minTime);
          max = new Date(maxTime);
        }
        
        setMinDate(min);
        setMaxDate(max);

        const institutionGroups = InvestmentSummary.reduce((groups: { [key: string]: { totalValue: number, minDate: Date } }, investment) => {
          if (!groups[investment.institution_name]) {
            groups[investment.institution_name] = {
              totalValue: 0,
              minDate: new Date(),
            };
          }
          groups[investment.institution_name].totalValue += investment.investment_value_in_native_currency ?? 0;
          
          if (investment.initial_investment_date && new Date(investment.initial_investment_date) < groups[investment.institution_name].minDate) {
            groups[investment.institution_name].minDate = new Date(investment.initial_investment_date);
          }
          
          return groups;
        }, {});
        
        const institutionLabels = Object.keys(institutionGroups);
        const institutionValues = Object.values(institutionGroups).map(group => group.totalValue);
        const institutionMinDates = Object.values(institutionGroups).map(group => group.minDate);
        const totalInstitutionInvestmentValue = institutionValues.reduce((total, value) => total + value, 0);
        
        const institutionPieChartData: PieChartData = {
          labels: institutionLabels,
          datasets: [{
            data: institutionValues.map(value => (value / totalInstitutionInvestmentValue) * 100),
            backgroundColor: institutionLabels.map(() => getRandomColor()),
          }],
        };
        
        const institutionTableRows = Object.entries(institutionGroups).map(([institution, { totalValue, minDate }], index) => ({
          id: index,
          institution_name: institution,
          investment_value_in_native_currency: totalValue,
          initial_investment_date: minDate.toLocaleDateString('en-ZA', { day: '2-digit', month: '2-digit', year: 'numeric' }),
        }));

        const menuItems = [
          {
            heading: 'Investment Type',
            items: ['ETF', 'Unit Trust', 'Forex', 'ETN', 'Hedge Fund', 'Deposit'],
            urls: ['http://localhost:3000/AddInvestment', '/investment-type/unit-trust', '/investment-type/forex', '/investment-type/etn', '/investment-type/hedge-fund', '/investment-type/deposit'],
          },
          {
            heading: 'Investment Currency',
            items: ['R', '$', '£', '€'],
            urls: ['/investment-currency/r', '/investment-currency/dollar', '/investment-currency/pound', '/investment-currency/euro'],
          },
          {
            heading: 'Institution',
            items: ['Institution 1', 'Institution 2', 'Institution 3'],
            urls: ['/institution/institution-1', '/institution/institution-2', '/institution/institution-3'],
          },
        ];

        setAllInvestmentValues(AllInvestmentGraphData);
        setAllInvestmentPieValues(pieChartData);
        setInvestmentSummary(InvestmentSummary);
        setInvestmentTypePieValues(investmentTypePieChartData);
        setInvestmentTypeTableRows(investmentTypeTableRows);
        setInvestmentCurrencyPieValues(currencyPieChartData);
        setInvestmentCurrencyTableRows(currencyTableRows);
        setInvestmentInstitutionPieValues(institutionPieChartData);
        setInvestmentInstitutionTableRows(institutionTableRows);
        setMenuItems(menuItems);
        setMinDate(min);
        setMaxDate(max);

      } catch (error) {
        console.error('Error fetching unit price:', error);
      }
    }

    fetchAllInvestmentValues();
  }, []);

  const toggleDarkMode = () => {
    setDarkMode(prevMode => !prevMode);
  };

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
      <div>
        {AllInvestmentValues && InvestmentSummary && AllInvestmentPieValues && InvestmentTypePieValues && InvestmentTypeTableRows && InvestmentCurrencyPieValues && InvestmentCurrencyTableRows && InvestmentInsitutionPieValues && InvestmentInsitutionTableRows ? (
          <Grid style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh', transition: 'background-color 0.3s' }}>
            <DrawerComponent menuItems={menuItems} />
            <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
              {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>
            <Grid container>
              <Grid item xs={12}>
                <Paper>
                  <LineGraph
                    data={AllInvestmentValues}
                    minDate={minDate}
                    maxDate={maxDate}
                    title="Investment values"
                    xAxisLabel="Date"
                    yAxisLabel="Value in R"
                  />
                </Paper>
              </Grid>
              <Grid item xs={12}>
                <Paper>
                  <StickyHeadTable columns={investment_summary_table_columns} rows={InvestmentSummary} />
                </Paper>
              </Grid>
              <Grid item xs={12}>
                <Paper>
                  <PieChart data={AllInvestmentPieValues} title="Individual Investment Values" theme={darkMode ? 'dark' : 'light'} />
                </Paper>
              </Grid>
            </Grid>
            <Grid container>
              <Grid item xs={12} md={6}>
                <Paper>
                  <PieChart data={InvestmentTypePieValues} title="Investment Values by Type" theme={darkMode ? 'dark' : 'light'} />
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper>
                  <StickyHeadTable columns={investment_type_table_columns} rows={InvestmentTypeTableRows} />
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper>
                  <PieChart data={InvestmentCurrencyPieValues} title="Investment Values by Currency" theme={darkMode ? 'dark' : 'light'} />
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper>
                  <StickyHeadTable columns={investment_currency_table_columns} rows={InvestmentCurrencyTableRows} />
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper>
                  <PieChart data={InvestmentInsitutionPieValues} title="Investment Values by Institution" theme={darkMode ? 'dark' : 'light'} />
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper>
                  <StickyHeadTable columns={investment_institution_table_columns} rows={InvestmentInsitutionTableRows} />
                </Paper>
              </Grid>
            </Grid>
          </Grid>
        ) : (
          <div className="loading-container" style={{ backgroundColor: darkMode ? '#222' : '#f1f2f4', minHeight: '100vh', transition: 'background-color 0.3s' }}>
            <IconButton onClick={toggleDarkMode} color="inherit" style={{ position: 'absolute', top: '10px', right: '10px' }}>
              {darkMode ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>
            <div>
              <CircularProgress />
            </div>
            <div style={{ marginLeft: '20px' }}>
              <p>Loading Investment Data...</p>
            </div>
          </div>
        )}
      </div>
    </ThemeProvider>
  );
}

export default AllInvestments;
