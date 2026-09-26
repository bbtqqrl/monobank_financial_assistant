import { Text as RNText, type TextProps } from 'react-native';

import { TEXT, useTheme, type TextVariant } from '@/theme';

export type Tone = 'ink' | 'inkSoft' | 'muted' | 'faint' | 'ghost' | 'accentText' | 'onPrimary' | 'danger';

type Props = TextProps & {
  variant?: TextVariant;
  tone?: Tone;
};

// Dynamic Type still works, but capped so cards don't fall apart
const MAX_FONT_SCALE = 1.3;

export function Text({ variant = 'body', tone = 'ink', style, ...rest }: Props) {
  const { c } = useTheme();
  return (
    <RNText
      maxFontSizeMultiplier={MAX_FONT_SCALE}
      {...rest}
      style={[TEXT[variant], { color: c[tone] }, style]}
    />
  );
}
