"use client";
import React from 'react';
import { Line } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js';
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
}

const AreaChart: React.FC<Props> = ({ data, title, theme = 'light' }) => {
  const options = {
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    stacked: false,
    plugins: {
      title: {
        display: true,
        text: title,
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: R${value.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`;
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Date'
        },
        ticks: {
          maxRotation: 45,
          minRotation: 45,
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Portfolio Value (R)'
        },
        ticks: {
          callback: (value: any) => `R${Number(value).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`
        }
      },
    },
  };

  return (
    <div>
      <div style={{ height: '400px', width: '100%' }}>
        <Line data={data} options={options} />
      </div>
    </div>
  );
};

export default AreaChart;
