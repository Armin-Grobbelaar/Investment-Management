"use client";

import { deepmerge } from '@mui/utils';
import ArrowDropDownRounded from '@mui/icons-material/ArrowDropDownRounded';
import { PaletteColor, createTheme, Theme, ThemeOptions, alpha } from '@mui/material/styles';

// =========================
// Module Augmentations
// =========================

declare module '@mui/material/styles' {
  interface Palette {
    primaryDark: PaletteColor;
    customColor?: Palette['primary'];
  }
  interface PaletteOptions {
    primaryDark?: PaletteOptions['primary'];
    customColor?: PaletteOptions['primary'];
  }

  interface TypographyVariants {
    fontWeightSemiBold: number;
    fontWeightExtraBold: number;
    fontFamilyCode: string;
  }
  interface TypographyVariantsOptions {
    fontWeightSemiBold?: number;
    fontWeightExtraBold?: number;
    fontFamilyCode?: string;
  }
}

declare module '@mui/material' {
  interface ButtonPropsColorOverrides {
    customColor: true;
  }
}

declare module '@mui/material/Button' {
  interface ButtonPropsVariantOverrides {
    code: true;
  }
}

// =========================
// Colors
// =========================
export const blue = {
  50: '#F0F7FF',
  100: '#C2E0FF',
  200: '#99CCF3',
  300: '#66B2FF',
  400: '#3399FF',
  main: '#007FFF',
  500: '#007FFF',
  600: '#0072E5',
  700: '#0059B2',
  800: '#004C99',
  900: '#003A75',
};

export const blueDark = {
  50: '#E2EDF8',
  100: '#CEE0F3',
  200: '#91B9E3',
  300: '#5090D3',
  main: '#5090D3',
  400: '#265D97',
  500: '#1E4976',
  600: '#173A5E',
  700: '#132F4C',
  800: '#001E3C',
  900: '#0A1929',
};

const grey = {
  50: '#F3F6F9',
  100: '#E7EBF0',
  200: '#E0E3E7',
  300: '#CDD2D7',
  400: '#B2BAC2',
  500: '#A0AAB4',
  600: '#6F7E8C',
  700: '#3E5060',
  800: '#2D3843',
  900: '#1A2027',
};

const systemFont = [
  '-apple-system',
  'BlinkMacSystemFont',
  '"Segoe UI"',
  'Roboto',
  '"Helvetica Neue"',
  'Arial',
  'sans-serif',
  '"Apple Color Emoji"',
  '"Segoe UI Emoji"',
  '"Segoe UI Symbol"',
];

// =========================
// Design Tokens
// =========================
export const getDesignTokens = (mode: 'light' | 'dark'): ThemeOptions => ({
  palette: {
    mode,
    primary: blue,
    primaryDark: blueDark,
    grey,
    text: {
      primary: mode === 'dark' ? '#fff' : grey[900],
      secondary: mode === 'dark' ? grey[400] : grey[700],
    },
    ...(mode === 'dark' && {
      background: { default: blueDark[800], paper: blueDark[900] },
    }),
  },
  typography: {
    fontFamily: ['"IBM Plex Sans"', ...systemFont].join(','),
    fontFamilyCode: ['Consolas','Menlo','Monaco','Andale Mono','Ubuntu Mono','monospace'].join(','),
    fontWeightSemiBold: 600,
    fontWeightExtraBold: 800,
    h1: { fontSize: '3rem', fontWeight: 800 },
    h2: { fontSize: '2.25rem', fontWeight: 800 },
  },
  shape: { borderRadius: 10 },
  spacing: 10,
});

// =========================
// Components
// =========================
export function getThemedComponents(theme: Theme): { components: Theme['components'] } {
  return {
    components: {
      MuiButtonBase: { defaultProps: { disableTouchRipple: true } },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          sizeLarge: {
            padding: '0.875rem 1rem',
            ...theme.typography.body1,
            fontWeight: 700,
          },
        },
        variants: [
          {
            props: { variant: 'code' },
            style: {
              fontFamily: theme.typography.fontFamilyCode,
            },
          },
        ],
      },
      MuiIconButton: {
        variants: [
          {
            props: { color: 'primary' },
            style: {
              borderRadius: theme.shape.borderRadius,
            },
          },
        ],
      },
      MuiSelect: { defaultProps: { IconComponent: ArrowDropDownRounded } },
    },
  };
}

// =========================
// Create Themes
// =========================
const darkTheme = createTheme(getDesignTokens('dark'));
export const brandingDarkTheme = deepmerge(darkTheme, getThemedComponents(darkTheme));

const lightTheme = createTheme(getDesignTokens('light'));
export const brandingLightTheme = deepmerge(lightTheme, getThemedComponents(lightTheme));

