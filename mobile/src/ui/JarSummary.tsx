import { StyleSheet, View } from 'react-native';

import { jarProgress, type Jar } from '@/api/jars';
import { FONT } from '@/lib/fonts';
import { formatMoney } from '@/lib/money';
import { useMask } from '@/lib/privacy';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Text } from '@/ui/Text';

const dayMonth = new Intl.DateTimeFormat('uk', { day: 'numeric', month: 'long' });
const dayMonthYear = new Intl.DateTimeFormat('uk', { day: 'numeric', month: 'long', year: 'numeric' });

function goalDay(date: Date, now: Date) {
  return (date.getFullYear() === now.getFullYear() ? dayMonth : dayMonthYear).format(date);
}

type Props = {
  jar: Jar;
  // when the goal is reached at the recent pace, if it can be told
  goalDate: Date | null;
  now?: Date;
};

// How much is in the jar, how far the goal is and when it's reached at this pace
export function JarSummary({ jar, goalDate, now = new Date() }: Props) {
  const { c, dark } = useTheme();
  const mask = useMask();
  const progress = jarProgress(jar);
  const money = (v: number) => mask(formatMoney(v, jar.currency_code, { cents: false }));
  const green = c.category.green;
  // past 100 once the goal is outgrown, unlike the bar
  const percent = jar.goal ? Math.floor((jar.balance / jar.goal) * 100) : null;

  return (
    <Glass contentStyle={styles.card}>
      <Text variant="labelCaps" tone="ghost">
        {progress === 1 ? 'Ціль зібрано' : 'Зібрано'}
      </Text>
      <View style={styles.amountRow}>
        <Text style={[TEXT.amountXl, styles.amount]}>{money(jar.balance)}</Text>
        {jar.goal ? (
          <Text tone="faint" style={styles.of}>
            з {money(jar.goal)}
          </Text>
        ) : null}
      </View>
      {progress !== null ? (
        <>
          <View style={[styles.track, { backgroundColor: withAlpha(c.shade, dark ? 0.12 : 0.08) }]}>
            <View style={[styles.fill, { width: `${progress * 100}%`, backgroundColor: green }]} />
          </View>
          <View style={styles.bottom}>
            <Text variant="rowCaption" tone="muted">
              {percent}% цілі
            </Text>
            {goalDate ? (
              <Text variant="rowCaption" style={[styles.pace, { color: green }]}>
                ≈ до {goalDay(goalDate, now)}
              </Text>
            ) : null}
          </View>
        </>
      ) : null}
      {jar.description ? (
        <Text variant="rowCaption" tone="faint">
          {jar.description}
        </Text>
      ) : null}
    </Glass>
  );
}

const styles = StyleSheet.create({
  // like BudgetSummary
  card: { paddingVertical: 14, paddingHorizontal: 16, gap: 10 },
  amountRow: { flexDirection: 'row', alignItems: 'baseline', gap: 8 },
  amount: { fontVariant: ['tabular-nums'] },
  of: { fontSize: 13 },
  track: { height: 10, borderRadius: 5, overflow: 'hidden' },
  fill: { height: 10, borderRadius: 5 },
  bottom: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  pace: { fontFamily: FONT.ui.semiBold },
});
