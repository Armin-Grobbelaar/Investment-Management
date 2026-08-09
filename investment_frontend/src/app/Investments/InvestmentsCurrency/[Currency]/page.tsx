"use client";
import React from 'react';
import { useParams } from 'next/navigation';
import InvestmentsDashboard from '../../InvestmentsDashboard';

export default function FilteredCurrencyPage() {
  const params = useParams();
  const filterValue = decodeURIComponent((params?.Currency as string) || '');

  return <InvestmentsDashboard filterType="unit_currency" filterValue={filterValue} />;
}
