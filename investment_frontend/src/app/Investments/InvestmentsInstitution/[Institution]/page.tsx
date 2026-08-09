"use client";
import React from 'react';
import { useParams } from 'next/navigation';
import InvestmentsDashboard from '../../InvestmentsDashboard';

export default function FilteredInstitutionPage() {
  const params = useParams();
  const filterValue = decodeURIComponent((params?.Institution as string) || '');

  return <InvestmentsDashboard filterType="institution_name" filterValue={filterValue} />;
}
