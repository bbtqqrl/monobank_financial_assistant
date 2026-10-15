import { useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { accountName, ownBalance, sortedAccounts, useAccountCurrencies, useAccounts } from '@/api/accounts';
import { REFRESH_FLASH, refreshAccounts } from '@/api/monobank';
import { useTransactions } from '@/api/transactions';
import { cardOrder, hiddenCards } from '@/lib/cardOrder';
import { thud } from '@/lib/haptics';
import { formatMoney } from '@/lib/money';
import { whenLabel } from '@/lib/time';
import { txRow } from '@/lib/txRow';
import { useExpandTabBarOnFocus } from '@/lib/tabBar';
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
  const qc = useQueryClient();
  useExpandTabBarOnFocus();
  const accounts = useAccounts();
  const order = cardOrder.useValue();
  const hidden = hiddenCards.useValue();
  const all = sortedAccounts(accounts.data ?? [], order);
  const visible = all.filter((a) => !hidden.includes(a.id));
  // with every card hidden (e.g. the last shown one was closed) the screen
  // would read as "not connected", so then they all show
  const shown = visible.length > 0 ? visible : all;
  const cards = shown.map((a) => ({
    key: a.id,
    label: a.masked_pan ? 'Баланс картки' : 'Баланс рахунку',
    balance: ownBalance(a),
    currency: a.currency_code,
    account: accountName(a),
    pan: a.masked_pan?.slice(-4),
    cardType: a.account_type,
    // the big number is own money; the bank's money on top of it only where there is some
    detail:
      a.credit_limit > 0
        ? { label: 'Кредитний ліміт', value: formatMoney(a.credit_limit, a.currency_code, { cents: false }) }
        : undefined,
  }));

  const recent = useTransactions({ limit: 5 });
  const currencies = useAccountCurrencies();
  const rows = currencies && recent.data?.map((t) => txRow(t, currencies, whenLabel(t.time)));

  const pull = usePullRefresh(async () => {
    // refetch() doesn't throw, it leaves the error in the query
    const [balances] = await Promise.all([refreshAccounts(qc), recent.refetch()]);
    return REFRESH_FLASH[balances];
  });

  // TODO: background="none" again once the map backdrop is in
  return (
    <Screen background="warm" pull={pull}>
      <Header
        title="Огляд"
        status={pull.status}
        left={{ icon: 'person', label: 'Профіль', onPress: () => router.push('/profile') }}
        // TODO: notifications screen
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
