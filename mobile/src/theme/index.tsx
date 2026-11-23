import { createContext, useContext, useState, type ReactNode } from 'react';
import { useWindowDimensions } from 'react-native';

import { palette, type PaletteColor } from './colors';

type Theme = {
  c: Record<PaletteColor, string>;
  outdoor: boolean;
  setOutdoor: (on: boolean) => void;
  /** Scales a font size; Outdoor mode makes everything 20% larger. */
  font: (size: number) => number;
  /** Minimum touch target height (48 dp normal, 56 dp Outdoor: glove-friendly). */
  touch: number;
  border: number;
};

const ThemeContext = createContext<Theme | null>(null);

// ponytail: Outdoor mode resets on app restart; persist it once a storage module lands (Checkpoint 3).
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [outdoor, setOutdoor] = useState(false);
  const theme: Theme = {
    c: outdoor ? { ...palette, surface: palette.bg } : palette,
    outdoor,
    setOutdoor,
    font: (size) => Math.round(size * (outdoor ? 1.2 : 1)),
    touch: outdoor ? 56 : 48,
    border: outdoor ? 3 : 2,
  };
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  const theme = useContext(ThemeContext);
  if (!theme) throw new Error('useTheme must be used inside ThemeProvider');
  return theme;
}

/** Tablets (and big phones in landscape) get a split view: list on the left, detail on the right. */
export function useIsTablet(): boolean {
  return useWindowDimensions().width >= 768;
}

/** Build guide: from 600 dp (tablets, phones in landscape) the tabs become a side rail. */
export function useSideRail(): boolean {
  return useWindowDimensions().width >= 600;
}
