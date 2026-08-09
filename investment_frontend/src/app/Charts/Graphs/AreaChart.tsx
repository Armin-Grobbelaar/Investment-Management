"use client";
import React from 'react';
import { Line } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js';
import { Box, Typography } from '@mui/material';

Chart.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

interface AreaChartData {
  datasets: {
    label: string;
    data: { x: string; y: number }[];
    fill: boolean;
    backgroundColor: string;
    borderColor: string;
    pointRadius: number;
  }[];
}

interface Props {
  data: AreaChartData;
  title: string;
  theme?: 'light' | 'dark';
  currencySymbol?: string;
  currencyCode?: string;
}

const AreaChart: React.FC<Props> = ({ data, title, theme = 'light', currencySymbol = 'R', currencyCode = 'ZAR' }) => {
  const isDark = theme === 'dark';
  const textColor = isDark ? '#e0e0e0' : '#2c3e50';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    stacked: false,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: {
          color: textColor,
          font: { size: 11, family: 'Roboto, sans-serif' },
        },
      },
      title: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: ${new Intl.NumberFormat('en-ZA', { style: 'currency', currency: currencyCode, maximumFractionDigits: 0 }).format(value)}`;
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Date',
          color: textColor,
        },
        ticks: {
          color: textColor,
          font: { size: 10 },
          maxRotation: 35,
          minRotation: 0,
        },
        grid: {
          color: gridColor,
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: `Portfolio Value (${currencySymbol})`,
          color: textColor,
        },
        ticks: {
          color: textColor,
          font: { size: 10 },
          callback: (value: any) => new Intl.NumberFormat('en-ZA', { style: 'currency', currency: currencyCode, maximumFractionDigits: 0 }).format(value),
        },
        grid: {
          color: gridColor,
        },
      },
    },
  };

  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {title && (
        <Typography variant="h6" align="center" sx={{ mb: 1, fontWeight: 'bold', color: textColor }}>
          {title}
        </Typography>
      )}
      <Box sx={{ flex: 1, width: '100%', minHeight: '280px', position: 'relative' }}>
        <Line data={data} options={options} />
      </Box>
    </Box>
  );
};

export default AreaChart;
