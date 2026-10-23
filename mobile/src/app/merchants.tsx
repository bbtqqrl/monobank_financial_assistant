import { useLocalSearchParams } from 'expo-router';
import { Fragment } from 'react';
import { ActivityIndicator, StyleSheet } from 'react-native';

import { useTopMerchants } from '@/api/analytics';
import { goBack } from '@/lib/nav';
import { monthTitle } from '@/lib/period';
import { usePullRefresh } from '@/lib/usePullRefresh';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Screen } from '@/ui/Screen';
import { Text } from '@/ui/Text';
import { MerchantDivider, MerchantRow } from '@/ui/TopMerchants';

// the backend gives at most this many in one go, plenty for a month
const LIMIT = 100;

// month= 'YYYY-MM', anything else falls back to this month
function monthOf(param: string | undefined) {
  const m = param?.match(/^(\d{4})-(\d{2})$/);
  const now = new Date();
  return m ? { year: Number(m[1]), month: Number(m[2]) - 1 } : { year: now.getFullYear(), month: now.getMonth() };
}

// Analytics › Найбільші витрати › Переглянути всі: every merchant of the month
export default function MerchantsScreen() {
  const params = useLocalSearchParams<{ month?: string }>();
  const month = monthOf(params.month);
  const merchants = useTopMerchants(month, LIMIT);
  const pull = usePullRefresh(async () => {
    const result = await merchants.refetch();
    if (result.isError) throw result.error;
  });
  const items = merchants.data?.items ?? [];

  return (
    <Screen background="warm" pull={pull}>
      <Header
        title="Найбільші витрати"
        small
        status={pull.status}
        left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
      />
      <Text variant="labelCaps" tone="ghost" style={styles.month}>
        {monthTitle(new Date(month.year, month.month, 1))}
      </Text>

      {merchants.isPending ? (
        <ActivityIndicator style={styles.message} />
      ) : merchants.isError ? (
        <Text tone="danger" style={styles.message}>
          Не вдалося завантажити витрати
        </Text>
      ) : (
        <Glass contentStyle={styles.card}>
          {items.map((m, i) => (
            <Fragment key={m.merchant_key}>
              {i > 0 && <MerchantDivider />}
              <MerchantRow merchant={m} />
            </Fragment>
          ))}
        </Glass>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  month: { textAlign: 'center', marginTop: -4 },
  message: { paddingVertical: 40, textAlign: 'center' },
  card: { paddingVertical: 4, paddingHorizontal: 16 },
});
