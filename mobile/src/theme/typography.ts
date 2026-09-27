import type { TextStyle } from 'react-native';

import { FONT } from '@/lib/fonts';

// Figma letter spacing is in %, RN wants points: size * pct / 100.
// Line height isn't set anywhere in the design, so it's fixed here:
// amounts 1.15, titles 1.25, everything else 1.35. Don't change later,
// every screen is laid out against these.
function style(fontFamily: string, fontSize: number, lh: number, pct = 0, extra: TextStyle = {}): TextStyle {
  return {
    fontFamily,
    fontSize,
    lineHeight: Math.round(fontSize * lh),
    letterSpacing: (fontSize * pct) / 100,
    ...extra,
  };
}

export const TEXT = {
  screenTitle: style(FONT.display.medium, 17, 1.25, -1),
  amountXl: style(FONT.ui.bold, 30, 1.15, -1),
  amountLg: style(FONT.ui.bold, 22, 1.15),
  labelCaps: style(FONT.ui.semiBold, 11.5, 1.35, 7, { textTransform: 'uppercase' }),
  labelSection: style(FONT.ui.semiBold, 13.5, 1.35),
  bodyStrong: style(FONT.ui.semiBold, 13.5, 1.35),
  body: style(FONT.ui.medium, 13, 1.35),
  rowTitle: style(FONT.ui.semiBold, 14, 1.35),
  rowAmount: style(FONT.ui.semiBold, 14.5, 1.15, 0, { fontVariant: ['tabular-nums'] }),
  rowCaption: style(FONT.ui.medium, 12, 1.35),
  button: style(FONT.ui.semiBold, 15, 1.25),
  link: style(FONT.ui.semiBold, 12.5, 1.35),
} satisfies Record<string, TextStyle>;

export type TextVariant = keyof typeof TEXT;
