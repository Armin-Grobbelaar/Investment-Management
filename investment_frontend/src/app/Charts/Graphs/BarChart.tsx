"use client";
import React from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
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
  const options = {
    indexAxis: type === 'horizontalBar' ? 'y' as const : 'x' as const,
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
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
        ticks: {
          maxRotation: type === 'verticalBar' ? 45 : 0,
          minRotation: type === 'verticalBar' ? 45 : 0,
        },
      },
      y: {
        ticks: {
          callback: (value: any) => `R${Number(value).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`
        }
      }
    },
  };

  return (
    <div>
      <div style={{ height: '400px', width: '100%' }}>
        <Bar data={data} options={options} />
      </div>
    </div>
  );
};

export default BarChart;
