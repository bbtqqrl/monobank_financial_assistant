import { Fragment } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

import type { Merchant } from '@/api/analytics';
import { categoryLook } from '@/lib/categories';
import { formatMoney } from '@/lib/money';
import { plural } from '@/lib/plural';
import { useMask } from '@/lib/privacy';
import { useTheme, withAlpha } from '@/theme';
import { CategoryChip } from '@/ui/CategoryChip';
import { Glass } from '@/ui/Glass';
import { Text } from '@/ui/Text';

// One merchant: its category's chip, how many purchases, how much in all
export function MerchantRow({ merchant }: { merchant: Merchant }) {
  const mask = useMask();
  return (
    <View style={styles.row}>
      <CategoryChip {...categoryLook(merchant.category?.slug, -1)} size={36} radius={12} />
      <View style={styles.text}>
        <Text variant="rowTitle" numberOfLines={1}>
          {merchant.name}
        </Text>
        <Text variant="rowCaption" tone="faint">
          {plural(merchant.purchase_count, ['покупка', 'покупки', 'покупок'])}
        </Text>
      </View>
      <Text variant="rowAmount">{mask(formatMoney(merchant.amount, undefined, { cents: false }))}</Text>
    </View>
  );
}

// the line between rows
export function MerchantDivider() {
  const { c } = useTheme();
  return <View style={[styles.divider, { backgroundColor: withAlpha(c.shade, 0.07) }]} />;
}

type Props = {
  items?: Merchant[];
  // all of the month's merchants, more than shown here
  total?: number;
  onSeeAll?: () => void;
};

// Where most of the month's money went, by merchant (Figma: Найбільші витрати)
export function TopMerchants({ items, total = 0, onSeeAll }: Props) {
  if (items && items.length === 0) return null;
  const more = !!items && total > items.length && !!onSeeAll;

  return (
    <Glass contentStyle={styles.card}>
      <View style={styles.head}>
        <Text variant="labelSection">Найбільші витрати</Text>
        {more ? (
          <Pressable accessibilityRole="button" hitSlop={10} onPress={onSeeAll}>
            <Text variant="link" tone="accentText">
              Переглянути всі
            </Text>
          </Pressable>
        ) : null}
      </View>
      {!items ? (
        <ActivityIndicator style={styles.loading} />
      ) : (
        items.map((m, i) => (
          <Fragment key={m.merchant_key}>
            {i > 0 && <MerchantDivider />}
            <MerchantRow merchant={m} />
          </Fragment>
        ))
      )}
    </Glass>
  );
}

const styles = StyleSheet.create({
  card: { paddingTop: 14, paddingHorizontal: 16, paddingBottom: 4 },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  loading: { marginVertical: 24 },
  divider: { height: 1 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10 },
  text: { flex: 1, gap: 2 },
});
