import type { StyleProp, TextStyle } from 'react-native';

import { formatMoney, UAH, type MoneyOptions } from '@/lib/money';
import { useTheme } from '@/theme';
import { Text } from '@/ui/Text';

type Props = MoneyOptions & {
  minor: number;
  currency?: number;
  variant?: 'amountXl' | 'amountLg' | 'rowAmount' | 'bodyStrong';
  // income in green, like in the design
  highlightIncome?: boolean;
  style?: StyleProp<TextStyle>;
};

// TODO: locale from i18n once it exists
export function Amount({ minor, currency = UAH, variant = 'rowAmount', highlightIncome, style, ...opts }: Props) {
  const { c } = useTheme();
  const income = highlightIncome && minor > 0;

  return (
    <Text variant={variant} numberOfLines={1} style={[income && { color: c.category.green }, style]}>
      {formatMoney(minor, currency, opts)}
    </Text>
  );
}
