// Same values as the Figma generator (design repo, figma-plugin/code.js).

const light = {
  bg: '#EFEDE8',
  sheet: '#F7F5F1',
  ink: '#1A1714',
  inkSoft: '#3A322B',
  muted: '#837C74',
  faint: '#9C948B',
  ghost: '#A49B91',
  cream: '#FBF8F3',
  accent: '#3A50B4',
  accentText: '#2D3E8C',
  accentOnDark: '#B0B9E1',
  accentFill: '#3A50B4',
  onPrimary: '#FBF8F3',
  cardA: '#2E2925',
  cardB: '#17150F',
  white: '#FFFFFF',
  shade: '#282018',
  shadow: '#282018',
  danger: '#C25A4E',
  warning: '#C98A2B',
  category: {
    green: '#1F8A5F',
    copper: '#C7622E',
    taxi: '#8E5BC4',
    slate: '#5C6B7A',
    brown: '#8A7250',
    plum: '#A8862F',
    dim: '#8E8880',
    teal: '#3E8A8B',
    blue: '#2D6FC4',
    clay: '#B45F55',
    rose: '#A8648A',
    olive: '#7A8A3E',
    neutral: '#6E665E',
  },
};

export type Colors = typeof light;

const dark: Colors = {
  bg: '#141318',
  sheet: '#1E1D24',
  ink: '#F0EDE7',
  inkSoft: '#D6CFC7',
  muted: '#B0A8A0',
  faint: '#9E968E',
  ghost: '#999189',
  cream: '#FBF8F3',
  accent: '#7C8FE8',
  accentText: '#7C8FE8',
  accentOnDark: '#A9B6EF',
  accentFill: '#4C63CE',
  onPrimary: '#F5F7FF',
  cardA: '#34333F',
  cardB: '#22212C',
  white: '#FFFFFF',
  shade: '#FFFFFF',
  shadow: '#000000',
  danger: '#DC8175',
  warning: '#D9A24A',
  category: {
    green: '#35B37E',
    copper: '#E08A55',
    taxi: '#A98BE6',
    slate: '#8FA2B4',
    brown: '#B99C74',
    plum: '#D2AC55',
    dim: '#9B948C',
    teal: '#57B3B4',
    blue: '#6E9BE8',
    clay: '#DC8175',
    rose: '#D08CB0',
    olive: '#A6B85E',
    neutral: '#A8A099',
  },
};

export const COLORS = { light, dark };

// Light glass is white at high alpha; on dark it has to be barely visible.
const WHITE_ALPHA_DARK: Record<number, number> = {
  0.95: 0.1, 0.92: 0.1, 0.9: 0.09, 0.82: 0.1, 0.8: 0.07,
  0.72: 0.06, 0.7: 0.09, 0.66: 0.055, 0.6: 0.05, 0.5: 0.04,
};

export function whiteAlpha(a: number, isDark: boolean) {
  return isDark ? (WHITE_ALPHA_DARK[a] ?? a) : a;
}

export function withAlpha(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}
