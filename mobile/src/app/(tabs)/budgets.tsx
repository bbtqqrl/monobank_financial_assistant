import { router } from 'expo-router';
import { Fragment } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { budgetRatio, useBudgets, type Budget } from '@/api/budgets';
import { hold } from '@/lib/haptics';
import { usePullRefresh } from '@/lib/usePullRefresh';
import { useTheme, withAlpha } from '@/theme';
import { BudgetRow } from '@/ui/BudgetRow';
import { BudgetSummary } from '@/ui/BudgetSummary';
import { Button } from '@/ui/Button';
import { EmptyState } from '@/ui/EmptyState';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Icon } from '@/ui/icons/Icon';
import { Screen } from '@/ui/Screen';
import { Text } from '@/ui/Text';

const newBudget = () => router.push('/budget');
const openBudget = (id: number) => router.push({ pathname: '/budget/[id]', params: { id: String(id) } });
const editBudget = (id: number) => {
  hold();
  router.push({ pathname: '/budget', params: { id: String(id) } });
};

// the ones over their limit come first, then the closest to it
const byPressure = (a: Budget, b: Budget) => budgetRatio(b) - budgetRatio(a);

// Monthly limits per category: what's left overall and per category
// (Figma: 09 · Бюджети)
export default function BudgetsScreen() {
  const { c } = useTheme();
  const budgets = useBudgets();
  const pull = usePullRefresh(async () => {
    const result = await budgets.refetch();
    if (result.isError) throw result.error;
  });
  const list = [...(budgets.data ?? [])].sort(byPressure);
  const over = list.filter((b) => budgetRatio(b) > 1);

  return (
    <Screen background="green" pull={pull}>
      <Header
        title="Бюджети"
        status={pull.status}
        right={{ icon: 'plus', label: 'Новий бюджет', weight: 2.2, onPress: newBudget }}
      />

      {budgets.isPending ? (
        <ActivityIndicator style={styles.loading} />
      ) : budgets.isError ? (
        <View style={styles.message}>
          <Text tone="danger">Не вдалося завантажити бюджети</Text>
          <Button kind="secondary" label="Спробувати ще" onPress={() => budgets.refetch()} />
        </View>
      ) : list.length === 0 ? (
        <View style={styles.empty}>
          <EmptyState
            icon="budget"
            title="Постав ліміт на категорію"
            caption="Наприклад, 3 000 ₴ на кафе в місяць. Тут буде видно, скільки ще лишилось"
          />
          <Button label="Новий бюджет" onPress={newBudget} />
        </View>
      ) : (
        <>
          <BudgetSummary budgets={list} />

          {over.length > 0 ? (
            <View
              style={[
                styles.alert,
                { backgroundColor: withAlpha(c.danger, 0.1), borderColor: withAlpha(c.danger, 0.24) },
              ]}
            >
              <View style={[styles.alertIcon, { backgroundColor: withAlpha(c.danger, 0.16) }]}>
                <Icon name="sparkle" size={17} color={c.danger} weight={1.8} />
              </View>
              <Text variant="bodyStrong" style={styles.alertText}>
                {over.length === 1
                  ? `${over[0]!.category.name} вже понад ліміт`
                  : `Понад ліміт: ${over.map((b) => b.category.name).join(', ')}`}
              </Text>
            </View>
          ) : null}

          <Glass contentStyle={styles.card}>
            <Text variant="labelCaps" tone="ghost">
              За категоріями
            </Text>
            {list.map((b, i) => (
              <Fragment key={b.id}>
                {i > 0 && <View style={[styles.divider, { backgroundColor: withAlpha(c.shade, 0.07) }]} />}
                <BudgetRow budget={b} onPress={() => openBudget(b.id)} onLongPress={() => editBudget(b.id)} />
              </Fragment>
            ))}
          </Glass>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  loading: { marginTop: 40 },
  message: { paddingVertical: 24, gap: 12, alignItems: 'center' },
  empty: { gap: 4, paddingTop: 40 },
  alert: { flexDirection: 'row', alignItems: 'center', gap: 12, borderRadius: 22, borderWidth: 1, paddingVertical: 12, paddingHorizontal: 15 },
  alertIcon: { width: 34, height: 34, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  alertText: { flex: 1, fontSize: 13.5 },
  // Figma: 12 16 4 16
  card: { paddingTop: 12, paddingHorizontal: 16, paddingBottom: 4 },
  divider: { height: 1 },
});
