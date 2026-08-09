"use client";
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon from '@mui/material/ListItemIcon';
import IconButton from '@mui/material/IconButton';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import MenuIcon from '@mui/icons-material/Menu';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import HomeIcon from '@mui/icons-material/Home';
import EditIcon from '@mui/icons-material/Edit';
import DescriptionIcon from '@mui/icons-material/Description';
import HomeWorkIcon from '@mui/icons-material/HomeWork';
import InsightsIcon from '@mui/icons-material/Insights';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import FilterAltIcon from '@mui/icons-material/FilterAlt';

interface MenuItem {
  heading: string;
  items: string[];
  urls: string[];
}

interface Props {
  menuItems?: MenuItem[];
}

const PAGE_LINKS = [
  { label: 'Dashboard', href: '/Investments', icon: HomeIcon },
  { label: 'Edit Data', href: '/EditInvestmentData', icon: EditIcon },
  { label: 'Factsheets', href: '/Factsheets', icon: DescriptionIcon },
  { label: 'Property Analysis', href: '/PropertyAnalysis', icon: HomeWorkIcon },
  { label: 'View Metrics', href: '/ViewInvestmentMetrics', icon: InsightsIcon },
  { label: 'IRR Analysis', href: '/IRRAnalysis', icon: TrendingUpIcon },
  { label: 'Net Worth', href: '/NetWorth', icon: AccountBalanceWalletIcon },
  { label: 'Predictions', href: '/ViewInvestmentPredictions', icon: InsightsIcon },
  { label: 'Bulk Import', href: '/BulkImport', icon: UploadFileIcon },
];

const DrawerComponent: React.FC<Props> = ({ menuItems: propMenuItems = [] }) => {
  const [open, setOpen] = useState<boolean>(false);
  const [fetchedMenuItems, setFetchedMenuItems] = useState<MenuItem[]>([]);
  const pathname = usePathname();

  useEffect(() => {
    async function fetchFilters() {
      try {
        const response = await axios.get('/api/dashboard_charts/Investments');
        setFetchedMenuItems(response.data.menu_items || []);
      } catch (e) {
        console.error("Failed to fetch filters:", e);
      }
    }
    if (propMenuItems.length === 0) {
        fetchFilters();
    }
  }, [propMenuItems.length]);

  const menuItems = propMenuItems.length > 0 ? propMenuItems : fetchedMenuItems;

  const handleToggleDrawer = () => setOpen(!open);

  return (
    <>
      <IconButton onClick={handleToggleDrawer} aria-label="Open navigation menu">
        {open ? <ChevronLeftIcon /> : <MenuIcon />}
      </IconButton>
      <Drawer variant="persistent" anchor="left" open={open}>
        <IconButton onClick={handleToggleDrawer}>
          <ChevronLeftIcon />
        </IconButton>
        <List sx={{ width: 260 }}>
          <ListItem>
            <ListItemText primary="Navigation" />
          </ListItem>
          {PAGE_LINKS.map((page, index) => {
            const PageIcon = page.icon;
            const isActive = pathname === page.href;
            return (
              <Link key={index} href={page.href} passHref style={{ textDecoration: 'none', color: 'inherit' }}>
                <ListItemButton
                  selected={isActive}
                  sx={{
                    '&:hover': { backgroundColor: 'action.hover' },
                    backgroundColor: isActive ? 'action.selected' : 'transparent',
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <PageIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText primary={page.label} />
                </ListItemButton>
              </Link>
            );
          })}
          {menuItems.length > 0 && (
            <>
              <ListItem sx={{ mt: 2 }}>
                <ListItemText primary="Filters" secondary="Filter the dashboard view" />
              </ListItem>
              {menuItems.map((menuItem, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <FilterAltIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={menuItem.heading} />
                  </ListItem>
                  {menuItem.items.map((item, subIndex) => (
                    <Link
                      key={subIndex}
                      href={menuItem.urls[subIndex]}
                      passHref
                      style={{ textDecoration: 'none', color: 'inherit' }}
                    >
                      <ListItemButton
                        sx={{
                          pl: 4,
                          '&:hover': { backgroundColor: 'action.hover' },
                        }}
                      >
                        <ListItemText primary={item} />
                      </ListItemButton>
                    </Link>
                  ))}
                </React.Fragment>
              ))}
            </>
          )}
        </List>
      </Drawer>
    </>
  );
};

export default DrawerComponent;
