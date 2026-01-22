// Responsive design utilities and breakpoints

export const breakpoints = {
  xs: 0,
  sm: 600,
  md: 900,
  lg: 1200,
  xl: 1536,
} as const;

export const containerMaxWidths = {
  xs: 444,    // 0px and up
  sm: 600,    // 600px and up
  md: 900,    // 900px and up
  lg: 1200,   // 1200px and up
  xl: 1536,   // 1536px and up
} as const;

export const spacing = {
  xs: 1,
  sm: 2,
  md: 3,
  lg: 4,
  xl: 6,
} as const;

export const typography = {
  // Responsive font sizes
  h1: {
    xs: '2rem',
    sm: '2.5rem',
    md: '3rem',
    lg: '3.5rem',
    xl: '4rem',
  },
  h2: {
    xs: '1.5rem',
    sm: '1.75rem',
    md: '2rem',
    lg: '2.25rem',
    xl: '2.5rem',
  },
  h3: {
    xs: '1.25rem',
    sm: '1.5rem',
    md: '1.75rem',
    lg: '2rem',
    xl: '2.25rem',
  },
  h4: {
    xs: '1.125rem',
    sm: '1.25rem',
    md: '1.5rem',
    lg: '1.75rem',
    xl: '2rem',
  },
  h5: {
    xs: '1rem',
    sm: '1.125rem',
    md: '1.25rem',
    lg: '1.5rem',
    xl: '1.75rem',
  },
  h6: {
    xs: '0.875rem',
    sm: '1rem',
    md: '1.125rem',
    lg: '1.25rem',
    xl: '1.5rem',
  },
} as const;

export const gridColumns = {
  xs: 12,
  sm: 12,
  md: 12,
  lg: 12,
  xl: 12,
} as const;

// Responsive spacing utilities
export const getResponsiveSpacing = (base: number, multiplier: number = 1) => {
  return base * multiplier * 8; // Convert to pixels (8px base unit)
};

// Responsive container utilities
export const getContainerPadding = (breakpoint: keyof typeof breakpoints) => {
  const paddingMap = {
    xs: 16,
    sm: 24,
    md: 32,
    lg: 40,
    xl: 48,
  };
  return paddingMap[breakpoint];
};

// Responsive grid utilities
export const getGridColumns = (breakpoint: keyof typeof breakpoints) => {
  return gridColumns[breakpoint];
};

// Media query utilities
export const mediaQuery = {
  up: (breakpoint: keyof typeof breakpoints) => `@media (min-width: ${breakpoints[breakpoint]}px)`,
  down: (breakpoint: keyof typeof breakpoints) => `@media (max-width: ${breakpoints[breakpoint] - 1}px)`,
  between: (min: keyof typeof breakpoints, max: keyof typeof breakpoints) => 
    `@media (min-width: ${breakpoints[min]}px) and (max-width: ${breakpoints[max] - 1}px)`,
  only: (breakpoint: keyof typeof breakpoints) => {
    const nextBreakpoint = Object.keys(breakpoints).indexOf(breakpoint) + 1;
    const nextBreakpointName = Object.keys(breakpoints)[nextBreakpoint] as keyof typeof breakpoints;
    if (nextBreakpointName) {
      return mediaQuery.between(breakpoint, nextBreakpointName);
    }
    return mediaQuery.up(breakpoint);
  },
} as const;

// Responsive component props utilities
export const responsiveProps = {
  // Grid responsive props
  grid: {
    xs: { xs: 12 },
    sm: { xs: 12, sm: 6 },
    md: { xs: 12, sm: 6, md: 4 },
    lg: { xs: 12, sm: 6, md: 4, lg: 3 },
    xl: { xs: 12, sm: 6, md: 4, lg: 3, xl: 2 },
  },
  
  // Card responsive props
  card: {
    xs: { width: '100%' },
    sm: { width: '100%' },
    md: { width: '100%' },
    lg: { width: '100%' },
    xl: { width: '100%' },
  },
  
  // Typography responsive props
  typography: {
    h1: {
      fontSize: typography.h1,
    },
    h2: {
      fontSize: typography.h2,
    },
    h3: {
      fontSize: typography.h3,
    },
    h4: {
      fontSize: typography.h4,
    },
    h5: {
      fontSize: typography.h5,
    },
    h6: {
      fontSize: typography.h6,
    },
  },
} as const;
