"use client";
import React, { useState } from 'react';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import MenuIcon from '@mui/icons-material/Menu';

interface MenuItem {
  heading: string;
  items: string[];
  urls: string[];
}

interface Props {
  menuItems: MenuItem[];
}

const DrawerComponent: React.FC<Props> = ({ menuItems }) => {
  const [open, setOpen] = useState<boolean>(false);

  const handleToggleDrawer = () => setOpen(!open);

  const handleMenuItemClick = (url: string) => {
    window.location.href = url;
  };

  return (
    <>
      <IconButton onClick={handleToggleDrawer}>
        {open ? <ChevronLeftIcon /> : <MenuIcon />}
      </IconButton>
      <Drawer variant="persistent" anchor="left" open={open}>
        <IconButton onClick={handleToggleDrawer}>
          <ChevronLeftIcon />
        </IconButton>
        <List>
          {menuItems.map((menuItem, index) => (
            <React.Fragment key={index}>
              <ListItem>
                <ListItemText primary={menuItem.heading} />
              </ListItem>
              {menuItem.items.map((item, subIndex) => (
                <ListItem
                  key={subIndex}
                  component="button"
                  onClick={() => handleMenuItemClick(menuItem.urls[subIndex])}
                >
                  <ListItemText primary={item} />
                </ListItem>
              ))}
            </React.Fragment>
          ))}
        </List>
      </Drawer>
    </>
  );
};

export default DrawerComponent;
