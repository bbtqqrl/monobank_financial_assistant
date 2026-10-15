import { router, useLocalSearchParams } from 'expo-router';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { useBudgets } from '@/api/budgets';
import { useTransactionPages } from '@/api/transactions';
import { categoryLook } from '@/lib/categories';
import { goBack } from '@/lib/nav';
import { periodRange, thisMonth } from '@/lib/period';
import { usePullRefresh } from '@/lib/usePullRefresh';
import { BudgetSummary } from '@/ui/BudgetSummary';
import { CategoryChip } from '@/ui/CategoryChip';
import { EmptyState } from '@/ui/EmptyState';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Screen } from '@/ui/Screen';
import { Text } from '@/ui/Text';
import { TxList } from '@/ui/TxList';

// One budget: how much of its limit is left, and this month's spending behind it
export default function BudgetScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const budgets = useBudgets();
  const budget = budgets.data?.find((b) => b.id === Number(id));
  const list = useTransactionPages(
    { category: budget?.category.id, ...periodRange(thisMonth()) },
    budget !== undefined,
  );
  const pull = usePullRefresh(async () => {
    const [b, l] = await Promise.all([budgets.refetch(), list.refetch()]);
    if (b.isError) throw b.error;
    if (l.isError) throw l.error;
  });

  const header = (
    <Header
      title={budget?.category.name ?? 'Бюджет'}
      small
      status={pull.status}
      left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
      right={
        budget
          ? {
              icon: 'pencil',
              label: 'Змінити ліміт',
              weight: 1.9,
              onPress: () => router.push({ pathname: '/budget', params: { id: String(budget.id) } }),
            }
          : undefined
      }
    />
  );

  if (!budget) {
    return (
      <Screen background="green">
        {header}
        {budgets.isPending ? (
          <ActivityIndicator style={styles.message} />
        ) : (
          <Text tone="faint" style={styles.message}>
            {budgets.isError ? 'Не вдалося завантажити бюджет' : 'Бюджет не знайдено'}
          </Text>
        )}
      </Screen>
    );
  }

  return (
    <TxList
      list={list}
      background="green"
      pull={pull}
      header={
        <View style={styles.top}>
          {header}
          <View style={styles.hero}>
            <CategoryChip {...categoryLook(budget.category.slug, -1)} size={62} radius={22} />
          </View>
          <BudgetSummary budgets={[budget]} />
        </View>
      }
      empty={
        <Glass>
          <EmptyState icon="cart" title="Витрат ще немає" caption="Тут будуть покупки з цієї категорії за місяць" />
        </Glass>
      }
    />
  );
}

const styles = StyleSheet.create({
  message: { paddingVertical: 40, textAlign: 'center' },
  top: { gap: 12, marginBottom: 8 },
  hero: { alignItems: 'center', paddingBottom: 2 },
});
