import { useColorScheme } from 'react-native';

import { COLORS, type Colors } from './colors';

export { TEXT, type TextVariant } from './typography';
export { whiteAlpha, withAlpha, type Colors } from './colors';

export type Theme = { dark: boolean; c: Colors };

// follows the system, or the choice from Profile (theme/preference.ts)
export function useTheme(): Theme {
  const dark = useColorScheme() === 'dark';
  return { dark, c: dark ? COLORS.dark : COLORS.light };
}
