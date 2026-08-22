"use client";
import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart, ArcElement, Tooltip, Legend, Title } from 'chart.js';
import { Box, Typography } from '@mui/material';

Chart.register(ArcElement, Tooltip, Legend, Title);

interface PieChartData {
  labels: string[];
  datasets: {
    data: number[];
    backgroundColor: string[];
  }[];
}

interface Props {
  data: PieChartData | null;
  title?: string;
  theme?: 'light' | 'dark';
}

const PieChart: React.FC<Props> = ({ data, title, theme = 'light' }) => {
  if (!data || !data.labels || data.labels.length === 0) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', width: '100%' }}>
        <Typography variant="body2" color="textSecondary">
          No data available for {title || 'chart'}
        </Typography>
      </Box>
    );
  }

  const isDark = theme === 'dark';
  const textColor = isDark ? '#e0e0e0' : '#2c3e50';

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '70%', // makes it a nice donut
    plugins: {
      legend: {
        display: true,
        position: 'bottom' as const,
        labels: {
          color: textColor,
          boxWidth: 12,
          padding: 10,
          font: {
            size: 11,
            family: 'Roboto, sans-serif'
          },
          usePointStyle: true,
        },
      },
      title: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const label = context.label || '';
            const value = context.parsed || 0;
            return `${label}: ${value.toFixed(2)}%`;
          }
        }
      }
    },
  };

  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
      {title && title.trim().length > 0 && (
        <Typography variant="h6" align="center" sx={{ mb: 1, fontWeight: 'bold', color: textColor }}>
          {title}
        </Typography>
      )}
      <Box sx={{ flex: 1, width: '100%', minHeight: '260px', maxHeight: '340px', position: 'relative' }}>
        <Doughnut data={data} options={chartOptions} />
      </Box>
    </Box>
  );
};

export default PieChart;
