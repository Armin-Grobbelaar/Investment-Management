"use client";
import React from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, LineController, LineElement, LinearScale, PointElement, Tooltip, Legend, TimeScale } from 'chart.js';
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
}

const LineGraph: React.FC<Props> = ({ data, minDate, maxDate, title, xAxisLabel, yAxisLabel }) => {
  return (
    <div>
      {data ? (
        <Line
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