"use client";
import React from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface ConfidenceIntervalData {
  prediction: { x: string; y: number }[];
  upperBound: { x: string; y: number }[];
  lowerBound: { x: string; y: number }[];
  historical?: { x: string; y: number }[];
}

interface Props {
  data: ConfidenceIntervalData;
  title: string;
  theme?: 'light' | 'dark';
}

const ConfidenceIntervalChart: React.FC<Props> = ({ data, title, theme = 'light' }) => {
  // Create continuous data combining historical and prediction
  const historicalData = data.historical?.slice(-10) || []; // Last 10 historical points
  const combinedData = [...historicalData.map(h => ({ x: new Date(h.x), y: h.y, type: 'historical' })),
                        ...data.prediction.map(p => ({ x: new Date(p.x), y: p.y, type: 'prediction' }))];

  // Create labels for combined timeline
  const dateLabels = combinedData.map((point, index) => {
    return point.x.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });

  const historicalLength = historicalData.length;
  const predictionLength = data.prediction.length;

  const confidenceData = {
    labels: dateLabels,
    datasets: [
      // Upper confidence bound (forms the ribbon above prediction line)
      {
        label: 'Upper Confidence Bound',
        data: combinedData.map((point, index) => {
          // Only show for prediction period
          if (index >= historicalLength) {
            const predictionIndex = index - historicalLength;
            return data.upperBound[predictionIndex]?.y;
          }
          return null;
        }),
        borderColor: 'rgba(102, 178, 255, 0.6)',
        backgroundColor: 'transparent',
        borderWidth: 1,
        borderDash: [3, 3],
        pointRadius: 0,
        tension: 0.4,
        fill: '+1', // Fill to lower bound below it
        order: 1,
        z: 15,
      },
      // Lower confidence bound (forms the ribbon below prediction line)
      {
        label: 'Lower Confidence Bound',
        data: combinedData.map((point, index) => {
          // Only show for prediction period
          if (index >= historicalLength) {
            const predictionIndex = index - historicalLength;
            return data.lowerBound[predictionIndex]?.y;
          }
          return null;
        }),
        borderColor: 'rgba(102, 178, 255, 0.6)',
        backgroundColor: theme === 'dark' ? 'rgba(102, 178, 255, 0.18)' : 'rgba(102, 178, 255, 0.15)',
        borderWidth: 1,
        borderDash: [3, 3],
        pointRadius: 0,
        tension: 0.4,
        fill: false,
        order: 2,
        z: 12,
      },
      // Prediction line (in the middle of the confidence ribbon)
      {
        label: 'Prediction Line',
        data: combinedData.map(point => point.y),
        borderColor: (context: any) => {
          const dataIndex = context.dataIndex;
          return dataIndex < historicalLength ? '#007FFF' : '#FF6B35'; // Blue for historical, orange for prediction
        },
        backgroundColor: 'transparent',
        borderWidth: (context: any) => {
          const dataIndex = context.dataIndex;
          return dataIndex < historicalLength ? 2 : 3; // Thicker for prediction
        },
        pointRadius: 0,
        pointHoverRadius: 6,
        pointBackgroundColor: (context: any) => {
          const dataIndex = context.dataIndex;
          return dataIndex < historicalLength ? '#007FFF' : '#FF6B35';
        },
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        tension: 0.4,
        fill: false,
        order: 3,
        z: 10, // Between confidence bounds
        segment: {
          borderColor: (context: any) => {
            return context.p0.parsed.x < historicalLength ? '#007FFF' : '#FF6B35';
          }
        }
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
        }
      },
      title: {
        display: true,
        text: title,
        padding: {
          bottom: 20
        }
      },
      tooltip: {
        backgroundColor: theme === 'dark' ? 'rgba(33, 33, 33, 0.9)' : 'rgba(255, 255, 255, 0.9)',
        titleColor: theme === 'dark' ? '#ffffff' : '#333333',
        bodyColor: theme === 'dark' ? '#ffffff' : '#666666',
        borderColor: '#007FFF',
        borderWidth: 2,
        cornerRadius: 8,
        displayColors: true,
        callbacks: {
          title: (tooltipItems: any) => {
            // Use the raw index to get full date
            const index = tooltipItems[0].dataIndex;
            const actualDate = data.prediction[index]?.x;
            if (actualDate) {
              const date = new Date(actualDate);
              return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
              });
            }
            return '';
          },
          label: (context: any) => {
            let label = context.dataset.label || '';
            let value = context.parsed.y;

            // Format as currency
            if (typeof value === 'number') {
              label += `: R${value.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`;
            }

            // Add confidence info for prediction line
            if (label.includes('Prediction') && context.dataIndex < data.upperBound.length) {
              const upper = data.upperBound[context.dataIndex].y;
              const lower = data.lowerBound[context.dataIndex].y;
              const range = upper - lower;
              const confInfo = `\nRange: R${lower.toLocaleString('en-ZA', { maximumFractionDigits: 0 })} - R${upper.toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`;
              label += confInfo;
            }

            return label;
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
          text: 'Price (R)',
        },
        ticks: {
          callback: (value: any) => `R${Number(value).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`,
        }
      },
    },
    elements: {
      point: {
        hoverRadius: 6,
        hoverBorderWidth: 3,
      }
    },
  };

  return (
    <div>
      <div style={{ height: '500px', width: '100%', position: 'relative' }}>
        <Line data={confidenceData} options={options} />
      </div>
      {/* Confidence Interval Legend */}
      <div style={{
        marginTop: '16px',
        padding: '12px',
        backgroundColor: theme === 'dark' ? 'rgba(33, 33, 33, 0.8)' : 'rgba(248, 249, 250, 0.8)',
        borderRadius: '8px',
        border: '1px solid',
        borderColor: theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          justifyContent: 'center',
          flexWrap: 'wrap'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div style={{
              width: '16px',
              height: '12px',
              backgroundColor: '#FF6B35',
              borderRadius: '2px'
            }}></div>
            <span style={{
              fontSize: '14px',
              fontWeight: '500',
              color: theme === 'dark' ? '#ffffff' : '#333333'
            }}>
              AI Prediction
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div style={{
              width: '16px',
              height: '12px',
              backgroundColor: 'rgba(0, 123, 255, 0.3)',
              border: '1px solid #66B2FF',
              borderRadius: '2px'
            }}></div>
            <span style={{
              fontSize: '14px',
              fontWeight: '500',
              color: theme === 'dark' ? '#ffffff' : '#333333'
            }}>
              Confidence Interval (95%)
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div style={{
              width: '12px',
              height: '0',
              borderTop: `2px dashed #66B2FF`
            }}></div>
            <span style={{
              fontSize: '14px',
              fontWeight: '500',
              color: theme === 'dark' ? '#ffffff' : '#333333'
            }}>
              Upper/Lower Bounds
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfidenceIntervalChart;
