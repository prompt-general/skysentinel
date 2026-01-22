import React from 'react';
import { Grid, GridProps } from '@mui/material';
import { useResponsive } from '../../hooks/useResponsive';

interface ResponsiveGridProps extends GridProps {
  spacing?: number;
  mobileSpacing?: number;
  tabletSpacing?: number;
  desktopSpacing?: number;
}

const ResponsiveGrid: React.FC<ResponsiveGridProps> = ({
  children,
  spacing = 2,
  mobileSpacing,
  tabletSpacing,
  desktopSpacing,
  sx,
  ...props
}) => {
  const { isMobile, isTablet, isDesktop } = useResponsive();
  
  const getResponsiveSpacing = () => {
    if (isMobile && mobileSpacing !== undefined) return mobileSpacing;
    if (isTablet && tabletSpacing !== undefined) return tabletSpacing;
    if (isDesktop && desktopSpacing !== undefined) return desktopSpacing;
    return spacing;
  };
  
  return (
    <Grid
      container
      spacing={getResponsiveSpacing()}
      sx={sx}
      {...props}
    >
      {children}
    </Grid>
  );
};

export default ResponsiveGrid;
