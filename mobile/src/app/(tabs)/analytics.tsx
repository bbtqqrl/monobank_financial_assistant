import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { monthParam, useCategoryShares, useSpending, useTopMerchants } from '@/api/analytics';
import { useOldestMonth } from '@/api/transactions';
import { monthTitle, type MonthKey } from '@/lib/period';
import { usePullRefresh } from '@/lib/usePullRefresh';
import { Button } from '@/ui/Button';
import { CategoryDonut } from '@/ui/CategoryDonut';
import { Header } from '@/ui/Header';
import { MonthSwitcher } from '@/ui/MonthSwitcher';
import { Screen } from '@/ui/Screen';
import { SpendingCard } from '@/ui/SpendingCard';
import { Text } from '@/ui/Text';
import { TopMerchants } from '@/ui/TopMerchants';

const TOP_CATEGORIES = 5;
const TOP_MERCHANTS = 5;

const currentMonth = (now = new Date()): MonthKey => ({ year: now.getFullYear(), month: now.getMonth() });
const shift = ({ year, month }: MonthKey, by: number): MonthKey => {
  const d = new Date(year, month + by, 1);
  return { year: d.getFullYear(), month: d.getMonth() };
};

// One month at a glance: what it cost, where it went and to whom
// (Figma: Аналітика › Підсумок)
export default function AnalyticsScreen() {
  const [month, setMonth] = useState(currentMonth);
  const now = currentMonth();
  const isCurrent = month.year === now.year && month.month === now.month;
  // nothing to show before the first transaction
  const oldest = useOldestMonth().data;
  const isOldest = !!oldest && month.year * 12 + month.month <= oldest.year * 12 + oldest.month;

  const spending = useSpending(month);
  const categories = useCategoryShares(month, TOP_CATEGORIES);
  const merchants = useTopMerchants(month, TOP_MERCHANTS);
  const pull = usePullRefresh(async () => {
    const results = await Promise.all([spending.refetch(), categories.refetch(), merchants.refetch()]);
    const failed = results.find((r) => r.isError);
    if (failed) throw failed.error;
  });

  const failed = spending.isError && !spending.data;
  const retry = () => {
    spending.refetch();
    categories.refetch();
    merchants.refetch();
  };

  return (
    <Screen background="warm" tab pull={pull}>
      <Header title="Аналітика" status={pull.status} />

      <MonthSwitcher
        title={monthTitle(new Date(month.year, month.month, 1))}
        onPrev={isOldest ? undefined : () => setMonth((m) => shift(m, -1))}
        onNext={isCurrent ? undefined : () => setMonth((m) => shift(m, 1))}
      />

      {failed ? (
        <View style={styles.message}>
          <Text tone="danger">Не вдалося завантажити аналітику</Text>
          <Button kind="secondary" label="Спробувати ще" onPress={retry} />
        </View>
      ) : (
        <>
          <SpendingCard year={month.year} month={month.month} spending={spending.data} />
          <CategoryDonut
            data={categories.data}
            onCategory={(id) =>
              router.push({ pathname: '/spending/[id]', params: { id: String(id), month: monthParam(month) } })
            }
          />
          <TopMerchants
            items={merchants.data?.items}
            total={merchants.data?.total}
            onSeeAll={() => router.push({ pathname: '/merchants', params: { month: monthParam(month) } })}
          />
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  message: { paddingVertical: 24, gap: 12, alignItems: 'center' },
});
