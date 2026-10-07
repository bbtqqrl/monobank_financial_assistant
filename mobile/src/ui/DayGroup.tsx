import { Fragment, type ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';

import { useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Text } from '@/ui/Text';
import { TxRow } from '@/ui/TxRow';

type Row = Omit<ComponentProps<typeof TxRow>, 'compact'> & { key: string | number };

type Props = {
  // "Сьогодні", "Вчора", "18 травня"
  label: string;
  // formatted sum for the day, empty to hide
  total?: string;
  rows: Row[];
};

// One day of the transactions list: caps label with the day total, then the
// rows on a single glass card
export function DayGroup({ label, total, rows }: Props) {
  const { c } = useTheme();

  return (
    <View style={styles.group}>
      <View style={styles.head}>
        <Text variant="labelCaps" tone="onBackdrop">
          {label}
        </Text>
        {total ? (
          <Text variant="link" style={[styles.total, { color: c.category.neutral }]}>
            {total}
          </Text>
        ) : null}
      </View>
      <Glass radius={22} contentStyle={styles.card}>
        {rows.map(({ key, ...row }, i) => (
          <Fragment key={key}>
            {i > 0 && <View style={[styles.divider, { backgroundColor: withAlpha(c.shade, 0.07) }]} />}
            <TxRow {...row} />
          </Fragment>
        ))}
      </Glass>
    </View>
  );
}

const styles = StyleSheet.create({
  group: { gap: 9 },
  head: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  total: { fontSize: 12, fontVariant: ['tabular-nums'] },
  // Figma: 4 16 4 16
  card: { paddingVertical: 4, paddingHorizontal: 16 },
  divider: { height: 1 },
});
