import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Button,
  Grid,
} from '@mui/material';

interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'text' | 'outlined' | 'contained';
  color?: 'primary' | 'secondary' | 'error' | 'inherit' | 'success' | 'warning' | 'info';
}

interface DialogComponentProps {
  open: boolean;
  onClose: () => void;
  mainHeading: string; // New prop for the main heading
  headings: string[];
  values: (string | number | undefined)[];
  buttons: ButtonProps[];
}

const DialogComponent: React.FC<DialogComponentProps> = ({
  open,
  onClose,
  mainHeading,
  headings,
  values,
  buttons,
}) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{mainHeading}</DialogTitle> {/* Display the main heading */}
      <DialogContent>
        <Grid container spacing={2}>
          {headings.map((heading, index) => (
            <Grid item xs={12} key={index}>
              <Typography variant="h6" fontWeight="bold">
                {heading}
              </Typography>
              <Typography variant="body1" style={{ marginLeft: '16px' }}>
                {values[index] !== undefined ? values[index] : ''}
              </Typography>
            </Grid>
          ))}
        </Grid>
      </DialogContent>
      <DialogActions>
        {buttons.map((button, index) => (
          <Button
            key={index}
            onClick={button.onClick}
            variant={button.variant || 'text'}
            color={button.color || 'primary'}
          >
            {button.label}
          </Button>
        ))}
      </DialogActions>
    </Dialog>
  );
};

export default DialogComponent;