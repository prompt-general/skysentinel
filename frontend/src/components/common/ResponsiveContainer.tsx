import React from 'react';
import { Box, BoxProps } from '@mui/material';
import { useResponsive } from '../../hooks/useResponsive';

interface ResponsiveContainerProps extends BoxProps {
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | false;
  disableGutters?: boolean;
  disablePadding?: boolean;
}

const ResponsiveContainer: React.FC<ResponsiveContainerProps> = ({
  children,
  maxWidth = 'lg',
  disableGutters = false,
  disablePadding = false,
  sx,
  ...props
}) => {
  const { isMobile, isTablet } = useResponsive();
  
  const getPadding = () => {
    if (disablePadding) return 0;
    if (disableGutters) return 2;
    if (isMobile) return 2;
    if (isTablet) return 3;
    return 4;
  };
  
  const getMaxWidth = () => {
    if (maxWidth === false) return '100%';
    return maxWidth;
  };
  
  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: getMaxWidth(),
        mx: 'auto',
        px: getPadding(),
        ...sx
      }}
      {...props}
    >
      {children}
    </Box>
  );
};

export default ResponsiveContainer;
