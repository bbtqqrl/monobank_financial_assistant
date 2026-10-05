import { Fragment, type ComponentProps } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Text } from '@/ui/Text';
import { TxRow } from '@/ui/TxRow';

type Row = Omit<ComponentProps<typeof TxRow>, 'compact'> & { key: string | number };

type Props = {
  // undefined while loading
  rows?: Row[];
  error?: string;
  onSeeAll?: () => void;
};

// "Останні транзакції" on Overview
export function RecentCard({ rows, error, onSeeAll }: Props) {
  const { c } = useTheme();
  const divider = <View style={[styles.divider, { backgroundColor: withAlpha(c.shade, 0.07) }]} />;

  return (
    <Glass contentStyle={styles.card}>
      <View style={styles.head}>
        <Text variant="labelSection">Останні транзакції</Text>
        <Pressable accessibilityRole="button" hitSlop={10} onPress={onSeeAll}>
          <Text variant="link" tone="accentText">
            Переглянути всі
          </Text>
        </Pressable>
      </View>

      {error ? (
        <Text tone="faint" style={styles.note}>
          {error}
        </Text>
      ) : !rows ? (
        [0, 1, 2].map((i) => (
          <Fragment key={i}>
            {i > 0 && divider}
            <SkeletonRow />
          </Fragment>
        ))
      ) : rows.length === 0 ? (
        <Text tone="faint" style={styles.note}>
          Тут зʼявляться твої витрати
        </Text>
      ) : (
        rows.map(({ key, ...row }, i) => (
          <Fragment key={key}>
            {i > 0 && divider}
            <TxRow {...row} compact />
          </Fragment>
        ))
      )}
    </Glass>
  );
}

function SkeletonRow() {
  const { c } = useTheme();
  const bar = { backgroundColor: withAlpha(c.shade, 0.07) };
  return (
    <View style={styles.skeleton}>
      <View style={[styles.skeletonChip, bar]} />
      <View style={styles.skeletonText}>
        <View style={[styles.skeletonLine, bar, { width: '55%' }]} />
        <View style={[styles.skeletonLine, bar, { width: '35%' }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  // Figma: 13 16 4 16
  card: { paddingTop: 13, paddingHorizontal: 16, paddingBottom: 4 },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 2 },
  divider: { height: 1 },
  note: { paddingVertical: 14 },
  skeleton: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 6 },
  skeletonChip: { width: 38, height: 38, borderRadius: 13 },
  skeletonText: { flex: 1, gap: 7 },
  skeletonLine: { height: 10, borderRadius: 5 },
});
