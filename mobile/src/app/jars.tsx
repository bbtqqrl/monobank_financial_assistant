import { router } from 'expo-router';
import { Fragment } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { useMe } from '@/api/auth';
import { useJars } from '@/api/monobank';
import { formatMoney, UAH } from '@/lib/money';
import { goBack } from '@/lib/nav';
import { useMask } from '@/lib/privacy';
import { usePullRefresh } from '@/lib/usePullRefresh';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { EmptyState } from '@/ui/EmptyState';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { JarRow } from '@/ui/JarRow';
import { Screen } from '@/ui/Screen';
import { Text } from '@/ui/Text';

const openJar = (id: number) => router.push({ pathname: '/jar/[id]', params: { id: String(id) } });

// Every jar, from the jars plate on Overview
export default function JarsScreen() {
  const { c } = useTheme();
  const mask = useMask();
  const me = useMe();
  const jars = useJars(!!me.data?.mono_client_id);
  const active = (jars.data ?? []).filter((j) => j.is_active);
  const total = active.filter((j) => j.currency_code === UAH).reduce((s, j) => s + j.balance, 0);
  const pull = usePullRefresh(async () => {
    const result = await jars.refetch();
    if (result.isError) throw result.error;
  });

  return (
    <Screen background="green" pull={pull}>
      <Header
        title="Банки"
        status={pull.status}
        left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
      />

      {jars.isPending ? (
        <ActivityIndicator style={styles.loading} />
      ) : active.length === 0 ? (
        <Glass>
          <EmptyState icon="jar" title="Банок поки немає" caption="Банки з monobank зʼявляться тут самі" />
        </Glass>
      ) : (
        <>
          <Glass contentStyle={styles.summary}>
            <Text variant="labelCaps" tone="ghost">
              Разом у банках
            </Text>
            <Text style={[TEXT.amountXl, styles.total]}>{mask(formatMoney(total, UAH, { cents: false }))}</Text>
          </Glass>
          <Glass contentStyle={styles.card}>
            {active.map((j, i) => (
              <Fragment key={j.id}>
                {i > 0 && <View style={[styles.divider, { backgroundColor: withAlpha(c.shade, 0.07) }]} />}
                <JarRow jar={j} onPress={() => openJar(j.id)} />
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
  summary: { paddingVertical: 14, paddingHorizontal: 16, gap: 4 },
  total: { fontVariant: ['tabular-nums'] },
  card: { paddingTop: 4, paddingHorizontal: 16, paddingBottom: 4 },
  divider: { height: 1 },
});
