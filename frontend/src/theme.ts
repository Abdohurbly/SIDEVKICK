import { createTheme, ThemeOptions } from '@mui/material/styles';
import { PaletteMode } from '@mui/material';

const getDesignTokens = (mode: PaletteMode): ThemeOptions => ({
  palette: {
    mode,
    ...(mode === 'light'
      ? {
          // palette values for light mode
          primary: {
            main: '#1976d2', // Blue
            contrastText: '#ffffff',
          },
          secondary: {
            main: '#dc004e', // Pink
            contrastText: '#ffffff',
          },
          background: {
            default: '#f4f6f8',
            paper: '#ffffff',
          },
          text: {
            primary: '#2c3e50', // Darker grey for better contrast
            secondary: '#57606f', // Slightly lighter grey
          },
          action: {
            active: 'rgba(0, 0, 0, 0.54)',
            hover: 'rgba(0, 0, 0, 0.04)',
            selected: 'rgba(0, 0, 0, 0.08)',
            disabled: 'rgba(0, 0, 0, 0.26)',
            disabledBackground: 'rgba(0, 0, 0, 0.12)',
          },
          divider: 'rgba(0, 0, 0, 0.12)',
        }
      : {
          // palette values for dark mode
          primary: {
            main: '#90caf9', // Light Blue
            contrastText: 'rgba(0, 0, 0, 0.87)',
          },
          secondary: {
            main: '#f48fb1', // Light Pink
            contrastText: 'rgba(0, 0, 0, 0.87)',
          },
          background: {
            default: '#1a1a1a', // Slightly lighter dark
            paper: '#262626', // And paper
          },
          text: {
            primary: '#e0e0e0', // Lighter for dark mode
            secondary: '#b0b0b0', // Slightly darker secondary
          },
          action: {
            active: '#ffffff',
            hover: 'rgba(255, 255, 255, 0.08)',
            selected: 'rgba(255, 255, 255, 0.16)',
            disabled: 'rgba(255, 255, 255, 0.3)',
            disabledBackground: 'rgba(255, 255, 255, 0.12)',
          },
          divider: 'rgba(255, 255, 255, 0.12)',
        }),
  },
  typography: {
    fontFamily: [
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
    ].join(','),
    h6: {
        fontWeight: 500,
    }
  },
  shape: {
    borderRadius: 8, // Slightly more rounded corners
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: ({
          theme
        }) => ({
          backgroundColor: theme.palette.background.paper, // Use paper for appbar in both modes
          color: theme.palette.text.primary,
          borderBottom: `1px solid ${theme.palette.divider}`,
          boxShadow: theme.palette.mode === 'light' ? '0px 1px 3px rgba(0,0,0,0.1)' : '0px 1px 3px rgba(0,0,0,0.3)',
        }),
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: ({
          theme
        }) => ({
          backgroundColor: theme.palette.background.default, // Use default for drawer background
          borderRight: `1px solid ${theme.palette.divider}`
        }),
      },
    },
    MuiButton: {
        styleOverrides: {
            root: {
                textTransform: 'none',
                fontWeight: 600,
            },
            containedPrimary: ({
                theme
            }) => ({
                boxShadow: theme.shadows[2],
                '&:hover': {
                    boxShadow: theme.shadows[4],
                }
            })
        }
    },
    MuiPaper: {
        styleOverrides: {
            root: {
                // transition: 'background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out', // Smooth transitions
            },
            elevation1: ({ theme }) => ({
                boxShadow: theme.palette.mode === 'light' ? '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)' : '0 1px 3px 0 rgba(0, 0, 0, 0.3), 0 1px 2px 0 rgba(0, 0, 0, 0.24)',
            }),
            elevation2: ({ theme }) => ({
                boxShadow: theme.palette.mode === 'light' ? '0 3px 6px rgba(0,0,0,0.12), 0 3px 6px rgba(0,0,0,0.18)' : '0 3px 6px rgba(0,0,0,0.32), 0 3px 6px rgba(0,0,0,0.38)',
            }),
        }
    },
    MuiTreeItem: {
        styleOverrides: {
            label: ({
                theme
            }) => ({
                fontSize: '0.9rem',
                fontFamily: theme.typography.fontFamily,
            }),
            content: ({
                theme
            }) => ({
                paddingTop: theme.spacing(0.75),
                paddingBottom: theme.spacing(0.75),
                '&:hover': {
                    backgroundColor: theme.palette.action.hover,
                },
                '&.Mui-selected': {
                    backgroundColor: `${theme.palette.action.selected} !important`,
                    color: theme.palette.text.primary,
                    fontWeight: theme.typography.fontWeightMedium,
                    '&:hover': {
                        backgroundColor: `${theme.palette.action.selected} !important`,
                    }
                },
                '&.Mui-focused': {
                    backgroundColor: theme.palette.action.focus,
                },
            }),
        },
    },
    MuiAlert: {
        styleOverrides: {
            root: {
                borderRadius: '6px',
            }
        }
    }
  },
});

export const getAppTheme = (mode: PaletteMode) => createTheme(getDesignTokens(mode));
