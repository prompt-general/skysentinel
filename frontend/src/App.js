import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ApolloProvider } from '@apollo/client';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';

// Apollo Client
import client from './services/api';

// Layout Components
import Layout from './components/layout/Layout';

// Page Components
import Dashboard from './pages/Dashboard';
import Policies from './pages/Policies';
import Violations from './pages/Violations';
import AttackPaths from './pages/AttackPaths';
import Compliance from './pages/Compliance';
import Resources from './pages/Resources';
import CI_CD from './pages/CI_CD';
import Monitoring from './pages/Monitoring';
import Settings from './pages/Settings';

// Auth Components
import Login from './components/auth/Login';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Context Providers
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider as CustomThemeProvider } from './contexts/ThemeContext';
import { NotificationProvider } from './contexts/NotificationContext';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
    },
  },
});

// Material-UI theme
const muiTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#dc004e',
      light: '#ff5983',
      dark: '#9a0036',
    },
    error: {
      main: '#f44336',
      light: '#e57373',
      dark: '#d32f2f',
    },
    warning: {
      main: '#ff9800',
      light: '#ffb74d',
      dark: '#f57c00',
    },
    info: {
      main: '#2196f3',
      light: '#64b5f6',
      dark: '#1976d2',
    },
    success: {
      main: '#4caf50',
      light: '#81c784',
      dark: '#388e3c',
    },
    background: {
      default: '#fafafa',
      paper: '#ffffff',
    },
    text: {
      primary: '#212121',
      secondary: '#757575',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
    body1: {
      fontSize: '1rem',
    },
    body2: {
      fontSize: '0.875rem',
    },
    caption: {
      fontSize: '0.75rem',
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 16,
        },
      },
    },
  },
});

// Dark theme
const darkTheme = createTheme({
  ...muiTheme,
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
      light: '#e3f2fd',
      dark: '#42a5f5',
    },
    secondary: {
      main: '#f48fb1',
      light: '#fce4ec',
      dark: '#ad1457',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
    text: {
      primary: '#ffffff',
      secondary: '#b0b0b0',
    },
  },
});

function App() {
  return (
    <ApolloProvider client={client}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <CustomThemeProvider>
            <NotificationProvider>
              <Router>
                <Routes>
                  {/* Public Routes */}
                  <Route path="/login" element={<Login />} />
                  
                  {/* Protected Routes */}
                  <Route path="/" element={
                    <ProtectedRoute>
                      <Layout />
                    </ProtectedRoute>
                  }>
                    {/* Default redirect to dashboard */}
                    <Route index element={<Navigate to="/dashboard" replace />} />
                    
                    {/* Dashboard */}
                    <Route path="dashboard" element={<Dashboard />} />
                    
                    {/* Policies */}
                    <Route path="policies" element={<Policies />} />
                    <Route path="policies/new" element={<Policies mode="create" />} />
                    <Route path="policies/:id/edit" element={<Policies mode="edit" />} />
                    <Route path="policies/:id" element={<Policies mode="view" />} />
                    
                    {/* Violations */}
                    <Route path="violations" element={<Violations />} />
                    <Route path="violations/:id" element={<Violations mode="detail" />} />
                    
                    {/* Attack Paths */}
                    <Route path="attack-paths" element={<AttackPaths />} />
                    <Route path="attack-paths/:id" element={<AttackPaths mode="detail" />} />
                    
                    {/* Compliance */}
                    <Route path="compliance" element={<Compliance />} />
                    <Route path="compliance/:framework" element={<Compliance mode="framework" />} />
                    
                    {/* Resources */}
                    <Route path="resources" element={<Resources />} />
                    <Route path="resources/:id" element={<Resources mode="detail" />} />
                    
                    {/* CI/CD */}
                    <Route path="cicd" element={<CI_CD />} />
                    <Route path="cicd/evaluations/:id" element={<CI_CD mode="detail" />} />
                    
                    {/* Monitoring */}
                    <Route path="monitoring" element={<Monitoring />} />
                    <Route path="monitoring/ml-models" element={<Monitoring mode="ml-models" />} />
                    <Route path="monitoring/alerts" element={<Monitoring mode="alerts" />} />
                    <Route path="monitoring/analytics" element={<Monitoring mode="analytics" />} />
                    
                    {/* Settings */}
                    <Route path="settings" element={<Settings />} />
                    <Route path="settings/account" element={<Settings mode="account" />} />
                    <Route path="settings/team" element={<Settings mode="team" />} />
                    <Route path="settings/integrations" element={<Settings mode="integrations" />} />
                    <Route path="settings/preferences" element={<Settings mode="preferences" />} />
                  </Route>
                  
                  {/* Fallback route */}
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </Router>
            </NotificationProvider>
          </CustomThemeProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ApolloProvider>
  );
}

export default App;
