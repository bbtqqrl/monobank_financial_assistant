import { Link, router } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { accountLabel, ownBalance, sortedAccounts, useAccountCurrencies, useAccounts } from '@/api/accounts';
import { useTransactions } from '@/api/transactions';
import { whenLabel } from '@/lib/time';
import { txRow } from '@/lib/txRow';
import { TEXT, useTheme } from '@/theme';
import { BalanceCard } from '@/ui/BalanceCard';
import { BalanceCarousel } from '@/ui/BalanceCarousel';
import { Header } from '@/ui/Header';
import { RecentCard } from '@/ui/RecentCard';
import { Screen } from '@/ui/Screen';
import { Text } from '@/ui/Text';

// TODO: dev shortcuts, remove once the screen is done
const DEV_LINKS = [
  { label: 'Перевірки (dev)', href: '/dev/smoke' },
  { label: 'UI kit (dev)', href: '/dev/kit' },
] as const;

export default function OverviewScreen() {
  const { c } = useTheme();
  const accounts = useAccounts();
  const cards = sortedAccounts(accounts.data ?? []).map((a) => ({
    key: a.id,
    label: a.masked_pan ? 'Баланс картки' : 'Баланс рахунку',
    balance: ownBalance(a),
    currency: a.currency_code,
    account: accountLabel(a),
  }));

  const recent = useTransactions({ type: 'expense', limit: 5 });
  const currencies = useAccountCurrencies();
  const rows = recent.data?.map((t) => txRow(t, currencies, whenLabel(t.time)));

  const refresh = () => {
    accounts.refetch();
    recent.refetch();
  };

  return (
    <Screen background="none" refreshing={accounts.isRefetching || recent.isRefetching} onRefresh={refresh}>
      <Header
        title="Огляд"
        left={{ icon: 'person', label: 'Профіль', onPress: () => router.push('/profile') }}
        right={{ icon: 'bell', label: 'Сповіщення' }}
      />

      {accounts.isError && !accounts.data ? (
        <View style={styles.message}>
          <Text tone="danger">Не вдалося завантажити рахунки</Text>
          <Text tone="faint">{accounts.error.message}</Text>
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
        <BalanceCarousel cards={cards} />
      ) : (
        // still loading
        <BalanceCard />
      )}

      <RecentCard
        rows={rows}
        error={recent.isError && !recent.data ? 'Не вдалося завантажити транзакції' : undefined}
        onSeeAll={() => router.push('/transactions')}
      />

      <View style={styles.dev}>
        {DEV_LINKS.map((l) => (
          <Link key={l.label} href={l.href} style={[TEXT.bodyStrong, { color: c.accentText }]}>
            {l.label} →
          </Link>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  message: { paddingVertical: 24, gap: 6 },
  dev: { paddingTop: 24, gap: 14 },
});
