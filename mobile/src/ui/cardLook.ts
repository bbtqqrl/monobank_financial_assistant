import { UAH } from '@/lib/money';
import { withAlpha } from '@/theme';
import type { Colors } from '@/theme/colors';

// How an account's card is drawn, from the balance plate down to the tiny
// tile: the bank's cards retold in the app's palette.
export type CardLook = {
  // background-image layers
  background: string;
  // a light plate wants dark text
  light: boolean;
  // currency cards carry a coloured edge on the left
  stripe?: string;
  // Національний кешбек has its dot and dash
  motif?: 'dot';
  border?: string;
  // the colour of the glow the plate casts under itself
  tint: string;
  // the plate's darkest flat colour, for what sits right under its edge
  base: string;
};

// currency cards are told apart by colour
const STRIPES: Record<number, keyof Colors['category']> = { 840: 'green', 978: 'copper', 985: 'clay', 826: 'blue' };

const glow = (color: string, at: string, alpha: number, size = '120% 100%') =>
  `radial-gradient(${size} at ${at}, ${withAlpha(color, alpha)} 0%, ${withAlpha(color, 0)} 60%)`;

export function cardLook(type: string | undefined, currency: number, c: Colors, dark: boolean): CardLook {
  // the theme's card colours suit a light screen; on a dark one the plate
  // would come out lighter than the screen, so it goes deeper there
  const [from, to] = dark ? ['#24232B', '#0E0D12'] : [c.cardA, c.cardB];
  const base = `linear-gradient(152deg, ${from} 0%, ${to} 100%)`;
  const accent = glow(c.accent, '88% 4%', dark ? 0.36 : 0.55);
  const stripeKey = currency !== UAH ? STRIPES[currency] : undefined;

  if (stripeKey) {
    const stripe = c.category[stripeKey];
    return {
      background: [accent, glow(stripe, '4% 100%', 0.38, '90% 80%'), base].join(', '),
      light: false,
      stripe,
      tint: stripe,
      base: to,
    };
  }

  switch (type) {
    case 'white':
      return {
        background: [
          glow(c.accent, '88% 4%', 0.16),
          // a real white card would glare on the dark theme
          dark ? 'linear-gradient(152deg, #C9C2B7 0%, #A29A8F 100%)' : 'linear-gradient(152deg, #FFFFFF 0%, #E8E2D8 100%)',
        ].join(', '),
        light: true,
        border: 'rgba(40,32,24,0.1)',
        tint: c.shadow,
        base: dark ? '#A29A8F' : '#E8E2D8',
      };
    case 'yellow':
      return {
        background: [glow('#FFFFFF', '88% 4%', 0.35), 'linear-gradient(152deg, #EDCB7A 0%, #C99A3C 100%)'].join(', '),
        light: true,
        tint: c.category.plum,
        base: '#C99A3C',
      };
    case 'platinum':
      return {
        background: [glow('#FFFFFF', '88% 4%', 0.4), 'linear-gradient(152deg, #E2DDD5 0%, #A89F94 100%)'].join(', '),
        light: true,
        tint: c.shadow,
        base: '#A89F94',
      };
    case 'iron':
      return {
        background: [glow(c.accent, '88% 4%', 0.3), `linear-gradient(152deg, ${c.category.slate} 0%, #262B32 100%)`].join(
          ', ',
        ),
        light: false,
        tint: c.category.slate,
        base: '#262B32',
      };
    case 'madeInUkraine':
      return {
        background: [accent, glow(c.category.plum, '4% 100%', 0.42, '90% 80%'), base].join(', '),
        light: false,
        motif: 'dot',
        tint: c.category.plum,
        base: to,
      };
    case 'diia':
      return {
        background: [
          glow(c.accent, '82% 12%', 0.95, '75% 95%'),
          glow(c.category.teal, '12% 100%', 0.85, '70% 90%'),
          glow(c.category.plum, '92% 100%', 0.75, '50% 70%'),
          glow('#7FD1E8', '48% 60%', 0.35, '60% 60%'),
          base,
        ].join(', '),
        light: false,
        tint: c.accent,
        base: to,
      };
    default:
      return {
        background: [accent, glow('#C47C56', '4% 100%', 0.34, '90% 80%'), base].join(', '),
        light: false,
        tint: c.accent,
        base: to,
      };
  }
}
