import { useTheme, useMediaQuery } from '@mui/material';

interface ResponsiveValues {
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isLargeDesktop: boolean;
  currentBreakpoint: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

export const useResponsive = (): ResponsiveValues => {
  const theme = useTheme();
  
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.between('sm', 'lg'));
  const isDesktop = useMediaQuery(theme.breakpoints.between('lg', 'xl'));
  const isLargeDesktop = useMediaQuery(theme.breakpoints.up('xl'));
  
  const getCurrentBreakpoint = (): 'xs' | 'sm' | 'md' | 'lg' | 'xl' => {
    if (isLargeDesktop) return 'xl';
    if (isDesktop) return 'lg';
    if (isTablet) return 'md';
    if (isMobile) return 'sm';
    return 'xs';
  };
  
  return {
    isMobile,
    isTablet,
    isDesktop,
    isLargeDesktop,
    currentBreakpoint: getCurrentBreakpoint()
  };
};

export default useResponsive;
