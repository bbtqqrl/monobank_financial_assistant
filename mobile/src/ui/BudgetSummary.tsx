import { StyleSheet, View } from 'react-native';

import type { Budget } from '@/api/budgets';
import { FONT } from '@/lib/fonts';
import { formatMoney } from '@/lib/money';
import { useMask } from '@/lib/privacy';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Text } from '@/ui/Text';

const dayMonth = new Intl.DateTimeFormat('uk', { day: 'numeric', month: 'long' });

// How much is left of all the limits together until the month ends, and how
// much a day that leaves (Figma: Бюджети, «Залишок»)
export function BudgetSummary({ budgets, now = new Date() }: { budgets: Budget[]; now?: Date }) {
  const { c, dark } = useTheme();
  const mask = useMask();
  const total = budgets.reduce((s, b) => s + b.amount, 0);
  const spent = budgets.reduce((s, b) => s + b.current_amount, 0);
  const left = total - spent;
  const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  // today counts as a day still to spend
  const daysLeft = monthEnd.getDate() - now.getDate() + 1;
  const money = (v: number) => mask(formatMoney(v, undefined, { cents: false }));
  const ratio = total > 0 ? Math.min(spent / total, 1) : 0;

  return (
    <Glass contentStyle={styles.card}>
      <Text variant="labelCaps" tone="ghost">
        {left >= 0
          ? `Можна витратити до ${dayMonth.format(monthEnd)}`
          : budgets.length === 1
            ? 'Ліміт перевищено'
            : 'Ліміти перевищено'}
      </Text>
      <View style={styles.amountRow}>
        <Text style={[TEXT.amountXl, styles.amount, left < 0 && { color: c.danger }]}>{money(Math.abs(left))}</Text>
        <Text tone="faint" style={styles.of}>
          з {money(total)}
        </Text>
      </View>
      <View style={[styles.track, { backgroundColor: withAlpha(c.shade, dark ? 0.12 : 0.08) }]}>
        <View style={[styles.fill, { width: `${ratio * 100}%`, backgroundColor: left < 0 ? c.danger : c.accent }]} />
      </View>
      <View style={styles.bottom}>
        <Text variant="rowCaption" tone="muted">
          Витрачено {money(spent)}
        </Text>
        {left > 0 ? (
          <Text variant="rowCaption" tone="accentText" style={styles.perDay}>
            ≈ {money(Math.floor(left / daysLeft))} на день
          </Text>
        ) : null}
      </View>
    </Glass>
  );
}

const styles = StyleSheet.create({
  // Figma: 14 16 14 16, gap 10
  card: { paddingVertical: 14, paddingHorizontal: 16, gap: 10 },
  amountRow: { flexDirection: 'row', alignItems: 'baseline', gap: 8 },
  amount: { fontVariant: ['tabular-nums'] },
  of: { fontSize: 13 },
  track: { height: 10, borderRadius: 5, overflow: 'hidden' },
  fill: { height: 10, borderRadius: 5 },
  bottom: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  perDay: { fontFamily: FONT.ui.semiBold },
});
