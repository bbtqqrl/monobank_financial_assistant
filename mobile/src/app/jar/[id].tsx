import { useLocalSearchParams } from 'expo-router';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { useMe } from '@/api/auth';
import { jarGoalDate } from '@/api/jars';
import { useJars } from '@/api/monobank';
import { useTransactionPages } from '@/api/transactions';
import { goBack } from '@/lib/nav';
import { usePullRefresh } from '@/lib/usePullRefresh';
import { EmptyState } from '@/ui/EmptyState';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { JarSummary } from '@/ui/JarSummary';
import { JarTile } from '@/ui/JarRow';
import { Screen } from '@/ui/Screen';
import { Text } from '@/ui/Text';
import { TxList } from '@/ui/TxList';

// One jar: how much is saved, when the goal comes at this pace, and every
// deposit and withdrawal behind it
export default function JarScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const me = useMe();
  const jars = useJars(!!me.data?.mono_client_id);
  const jar = jars.data?.find((j) => j.id === Number(id));
  const list = useTransactionPages({ jar: jar?.id }, jar !== undefined);
  const pull = usePullRefresh(async () => {
    const [j, l] = await Promise.all([jars.refetch(), list.refetch()]);
    if (j.isError) throw j.error;
    if (l.isError) throw l.error;
  });

  const header = (
    <Header
      title={jar?.title ?? 'Банка'}
      small
      status={pull.status}
      left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
    />
  );

  if (!jar) {
    return (
      <Screen background="green">
        {header}
        {jars.isPending ? (
          <ActivityIndicator style={styles.message} />
        ) : (
          <Text tone="faint" style={styles.message}>
            {jars.isError ? 'Не вдалося завантажити банку' : 'Банку не знайдено'}
          </Text>
        )}
      </Screen>
    );
  }

  // the newest page is enough to tell the recent pace
  const recent = list.data?.pages[0]?.items ?? [];

  return (
    <TxList
      list={list}
      background="green"
      pull={pull}
      header={
        <View style={styles.top}>
          {header}
          <View style={styles.hero}>
            <JarTile size={62} />
          </View>
          <JarSummary jar={jar} goalDate={jarGoalDate(jar, recent)} />
        </View>
      }
      empty={
        <Glass>
          <EmptyState icon="jar" title="Поповнень ще немає" caption="Тут будуть усі поповнення і зняття з банки" />
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
