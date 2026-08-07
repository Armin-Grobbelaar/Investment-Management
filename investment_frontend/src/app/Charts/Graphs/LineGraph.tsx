"use client";
import React, { useRef, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, LineController, LineElement, LinearScale, PointElement, Tooltip, Legend, TimeScale, Chart } from 'chart.js';
import 'chartjs-adapter-date-fns';
ChartJS.register(LineController, LineElement, LinearScale, PointElement, Tooltip, Legend, TimeScale);

interface Point {
  x: Date;
  y: number;
}

interface LineGraphData {
  label: string;
  data: Point[];
  borderColour: string;
}

interface Props {
  data: LineGraphData[] | null;
  minDate?: Date;
  maxDate?: Date;
  title?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  onVisibilityChange?: (visibleDatasets: LineGraphData[]) => void;
}

const LineGraph: React.FC<Props> = ({ data, minDate, maxDate, title, xAxisLabel, yAxisLabel, onVisibilityChange }) => {
  const chartRef = useRef<any>(null);

  const getVisibleDatasets = (chart: any) => {
    if (!chart || !data || !chart.data?.datasets) return data || [];

    return data.filter((_, index) => {
      return chart.isDatasetVisible(index);
    });
  };

  const handleLegendClick = (event: any, legendItem: any, legend: any) => {
    // react-chartjs-2 ref directly gives us the Chart.js instance
    const chart = chartRef.current;
    if (!chart) {
      console.warn('Chart not available in ref');
      return;
    }

    // Default Chart.js legend click behavior (toggle visibility)
    const index = legendItem.datasetIndex;
    const meta = chart.getDatasetMeta(index);
    meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;

    chart.update();

    // Notify parent after the chart updates
    if (onVisibilityChange) {
      setTimeout(() => {
        const visibleDatasets = getVisibleDatasets(chart);
        console.log('Visibility change detected, visible datasets:', visibleDatasets.length);
        onVisibilityChange(visibleDatasets);
      }, 100);
    }
  };

  return (
    <div>
      {data ? (
        <Line
          ref={chartRef}
          data={{
            datasets: data.map(graphData => ({
              label: graphData.label,
              data: graphData.data,
              borderColor: graphData.borderColour,
            })),
          }}
          options={{
            plugins: {
              legend: {
                display: true,
                labels: {
                  boxWidth: 15,
                  usePointStyle: true,
                },
                onClick: handleLegendClick,
              },
              title: {
                display: true,
                text: title || '',
              },
            },
            scales: {
              x: {
                type: 'time',
                time: {
                  unit: 'day',
                  displayFormats: {
                    day: 'dd-MM-yyyy',
                  },
                },
                title: {
                  display: true,
                  text: xAxisLabel || '',
                },
                min: minDate?.toISOString(),
                max: maxDate?.toISOString(),
              },
              y: {
                title: {
                  display: true,
                  text: yAxisLabel || '',
                },
              },
            },
          }}
          //width={800}
          //height={800}
        />
      ) : (
        <p>No data available</p>
      )}
    </div>
  );
};

export default LineGraph;
