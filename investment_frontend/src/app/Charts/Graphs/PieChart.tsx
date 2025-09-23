"use client";
import React from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart, ArcElement } from 'chart.js';
import { ThemeProvider } from '@mui/material/styles';
import { brandingDarkTheme, brandingLightTheme } from '@/app/Themes/muiTheme';
Chart.register(ArcElement);

interface PieChartData {
    labels: string[];
    datasets: {
      data: number[];
      backgroundColor: string[];
    }[];
  }

interface Props {
    data: PieChartData;
    title?: string;
    theme?: 'light' | 'dark'; 
}

const PieChart: React.FC<Props> = ({ data, title, theme = 'light' }) => {
    const options = {
        plugins: {
            legend: {
                display: true,
                labels: {
                    boxWidth: 15,
                    usePointStyle: true,
                },
            },
        },
    };

    // Adjust outlineColor based on theme
    const outlineColor = theme === 'dark' ? 'white' : 'black';
    const customElements = [{
        afterDraw(chart: any) {
            const { ctx } = chart;
            const { chartArea } = chart;
            ctx.save();
            ctx.strokeStyle = outlineColor;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.rect(
                chartArea.left,
                chartArea.top,
                chartArea.right - chartArea.left,
                chartArea.bottom - chartArea.top
            );
            ctx.stroke();
            ctx.restore();
        }
    }];

    const chartOptions = {
        ...options,
        plugins: {
            ...options.plugins,
            customElements,
        },
    };

    return (
        <div>
            <h2>{title}</h2>
            <div style={{ height: '400px', width: '400px' }}>
                <ThemeProvider theme={theme === 'dark' ? brandingDarkTheme : brandingLightTheme}>
                    <Pie data={data} options={chartOptions} />
                </ThemeProvider>
            </div>
        </div>
    );
};

export default PieChart;