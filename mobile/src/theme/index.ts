import { useColorScheme } from 'react-native';

import { COLORS, type Colors } from './colors';

export { TEXT, type TextVariant } from './typography';
export { whiteAlpha, withAlpha, type Colors } from './colors';

export type Theme = { dark: boolean; c: Colors };

// TODO: manual light/dark switch from Profile
export function useTheme(): Theme {
  const dark = useColorScheme() === 'dark';
  return { dark, c: dark ? COLORS.dark : COLORS.light };
}
