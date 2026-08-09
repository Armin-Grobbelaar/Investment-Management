"use client";
import React from 'react';
import { useParams } from 'next/navigation';
import InvestmentsDashboard from '../../InvestmentsDashboard';

export default function FilteredTypePage() {
  const params = useParams();
  const filterValue = decodeURIComponent((params?.Type as string) || '');

  return <InvestmentsDashboard filterType="investment_type" filterValue={filterValue} />;
}
