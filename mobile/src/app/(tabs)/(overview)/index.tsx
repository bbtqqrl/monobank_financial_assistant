import { router } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { accountLabel, ownBalance, sortedAccounts, useAccountCurrencies, useAccounts } from '@/api/accounts';
import { useMonthSpend, useTransactions } from '@/api/transactions';
import { cardOrder } from '@/lib/cardOrder';
import { thud } from '@/lib/haptics';
import { formatMoney } from '@/lib/money';
import { monthLabel, whenLabel } from '@/lib/time';
import { txRow } from '@/lib/txRow';
import { usePullRefresh } from '@/lib/usePullRefresh';
import { BalanceCard } from '@/ui/BalanceCard';
import { BalanceCarousel } from '@/ui/BalanceCarousel';
import { Header } from '@/ui/Header';
import { RecentCard } from '@/ui/RecentCard';
import { Screen } from '@/ui/Screen';
import { Text } from '@/ui/Text';

const openCards = () => {
  thud();
  router.push('/cards');
};

export default function OverviewScreen() {
  const accounts = useAccounts();
  const spend = useMonthSpend();
  const month = monthLabel();
  const order = cardOrder.useValue();
  const cards = sortedAccounts(accounts.data ?? [], order).map((a) => {
    const spent = spend.data?.get(a.id);
    return {
      key: a.id,
      label: a.masked_pan ? 'Баланс картки' : 'Баланс рахунку',
      balance: ownBalance(a),
      currency: a.currency_code,
      account: accountLabel(a),
      cardType: a.account_type,
      spent: spent ? `${formatMoney(spent, a.currency_code, { cents: false })} за ${month}` : undefined,
    };
  });

  const recent = useTransactions({ limit: 5 });
  const currencies = useAccountCurrencies();
  const rows = currencies && recent.data?.map((t) => txRow(t, currencies, whenLabel(t.time)));

  const pull = usePullRefresh(() => Promise.allSettled([accounts.refetch(), spend.refetch(), recent.refetch()]));

  // TODO: background="none" again once the map backdrop is in
  return (
    <Screen background="warm" refreshing={pull.refreshing} onRefresh={pull.onRefresh}>
      <Header
        title="Огляд"
        left={{ icon: 'person', label: 'Профіль', onPress: () => router.push('/profile') }}
        right={{ icon: 'bell', label: 'Сповіщення' }}
      />

      {accounts.isError && !accounts.data ? (
        <View style={styles.message}>
          <Text tone="danger">Не вдалося завантажити рахунки</Text>
          {__DEV__ && <Text tone="faint">{accounts.error.message}</Text>}
          <Pressable accessibilityRole="button" hitSlop={8} onPress={() => accounts.refetch()}>
            <Text variant="link" tone="accentText">
              Спробувати ще
            </Text>
          </Pressable>
        </View>
      ) : accounts.data && cards.length === 0 ? (
        // TODO: link to the monobank connect screen
        <View style={styles.message}>
          <Text variant="bodyStrong">monobank ще не підключено</Text>
          <Text tone="faint">Щойно підключиш, тут зʼявиться баланс картки</Text>
        </View>
      ) : cards.length > 0 ? (
        <BalanceCarousel cards={cards} onLongPress={openCards} />
      ) : (
        // still loading
        <BalanceCard />
      )}

      <RecentCard
        rows={rows}
        error={recent.isError && !recent.data ? 'Не вдалося завантажити транзакції' : undefined}
        onSeeAll={() => router.push('/transactions')}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  message: { paddingVertical: 24, gap: 6 },
});
