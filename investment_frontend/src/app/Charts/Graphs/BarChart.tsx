"use client";
import React from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Box, Typography } from '@mui/material';

Chart.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface BarChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor: string[];
  }[];
}

interface Props {
  data: BarChartData;
  title: string;
  type?: 'verticalBar' | 'horizontalBar';
  theme?: 'light' | 'dark';
}

const BarChart: React.FC<Props> = ({ data, title, type = 'verticalBar', theme = 'light' }) => {
  const isDark = theme === 'dark';
  const textColor = isDark ? '#e0e0e0' : '#2c3e50';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

  const options = {
    indexAxis: type === 'horizontalBar' ? ('y' as const) : ('x' as const),
    responsive: true,
    maintainAspectRatio: false,
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
            const value = type === 'horizontalBar' ? context.parsed.x : context.parsed.y;
            return `${label}: R${Number(value).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`;
          },
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: textColor,
          font: { size: 10 },
          maxRotation: type === 'verticalBar' ? 35 : 0,
          minRotation: type === 'verticalBar' ? 0 : 0,
        },
        grid: {
          color: gridColor,
        },
      },
      y: {
        ticks: {
          color: textColor,
          font: { size: 10 },
          callback: (value: any) => `R${Number(value).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`,
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
        <Bar data={data} options={options} />
      </Box>
    </Box>
  );
};

export default BarChart;
