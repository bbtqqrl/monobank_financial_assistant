import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { FONT } from '@/lib/fonts';
import { isoDate, monthTitle, parseIso } from '@/lib/period';
import { useTheme, withAlpha } from '@/theme';
import { StepButton } from '@/ui/StepButton';
import { Text } from '@/ui/Text';

type Props = {
  // 'YYYY-MM-DD'; `to` is missing while only the first day is picked
  from?: string;
  to?: string;
  onChange: (from: string | undefined, to: string | undefined) => void;
  // one day instead of a range: every tap moves `from`
  single?: boolean;
};

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'];

// Month grid with a range: first tap sets the start, second the end.
// Days after today can't be picked.
export function RangeCalendar({ from, to, onChange, single = false }: Props) {
  const { c, dark } = useTheme();
  const today = isoDate(new Date());
  const [month, setMonth] = useState(() => {
    const d = from ? parseIso(from) : new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  const isCurrentMonth = month.getFullYear() === new Date().getFullYear() && month.getMonth() === new Date().getMonth();
  const shift = (n: number) => setMonth(new Date(month.getFullYear(), month.getMonth() + n, 1));

  // Monday-first offset of the 1st, then the days, padded to full weeks
  const lead = (month.getDay() + 6) % 7;
  const count = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const cells: (string | null)[] = [
    ...Array<null>(lead).fill(null),
    ...Array.from({ length: count }, (_, i) => isoDate(new Date(month.getFullYear(), month.getMonth(), i + 1))),
  ];
  while (cells.length % 7) cells.push(null);
  const weeks = Array.from({ length: cells.length / 7 }, (_, w) => cells.slice(w * 7, w * 7 + 7));

  const pick = (day: string) => {
    if (single || !from || to) onChange(day, undefined);
    else if (day < from) onChange(day, from);
    else onChange(from, day);
  };

  return (
    <View style={styles.box}>
      <View style={styles.nav}>
        <StepButton dir="prev" label="Попередній місяць" onPress={() => shift(-1)} />
        <Text variant="bodyStrong" style={styles.title}>
          {monthTitle(month)}
        </Text>
        <StepButton dir="next" label="Наступний місяць" onPress={() => shift(1)} disabled={isCurrentMonth} />
      </View>

      <View style={styles.week}>
        {WEEKDAYS.map((d) => (
          <Text key={d} variant="labelSection" tone="ghost" style={styles.weekday}>
            {d}
          </Text>
        ))}
      </View>

      {weeks.map((week, w) => (
        <View key={w} style={styles.week}>
          {week.map((day, i) => {
            if (!day) return <View key={i} style={styles.cell} />;
            const end = to ?? from;
            const edge = day === from || day === end;
            const inside = !!from && !!end && day > from && day < end;
            const future = day > today;
            return (
              <Pressable
                key={day}
                accessibilityRole="button"
                accessibilityState={{ selected: edge || inside, disabled: future }}
                disabled={future}
                onPress={() => pick(day)}
                style={[
                  styles.cell,
                  inside && { backgroundColor: withAlpha(c.accent, dark ? 0.22 : 0.12) },
                  edge && [styles.edge, { backgroundColor: c.accent }],
                ]}
              >
                <Text
                  style={[
                    styles.day,
                    edge && styles.dayEdge,
                    { color: edge ? c.white : inside ? c.accentText : c.ink },
                    future && styles.future,
                  ]}
                >
                  {parseIso(day).getDate()}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  box: { gap: 4 },
  nav: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  title: { fontSize: 15 },
  week: { flexDirection: 'row' },
  weekday: { flex: 1, textAlign: 'center', fontSize: 11.5 },
  cell: { flex: 1, height: 40, alignItems: 'center', justifyContent: 'center' },
  edge: { borderRadius: 13 },
  day: { fontSize: 14 },
  dayEdge: { fontFamily: FONT.ui.bold },
  future: { opacity: 0.35 },
});
