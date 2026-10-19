import { router } from 'expo-router';
import { Fragment } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';

import { useMe } from '@/api/auth';
import { useJars } from '@/api/monobank';
import { useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { JarRow } from '@/ui/JarRow';
import { Text } from '@/ui/Text';

// jars arrive with the monobank sync a moment after the screen opens
const APPEAR_MS = 220;

const openJar = (id: number) => router.push({ pathname: '/jar/[id]', params: { id: String(id) } });

// Бюджети › Банки: next to how much may still be spent, how much is saved.
// Not there at all for an account without jars.
export function JarsCard() {
  const { c } = useTheme();
  const me = useMe();
  const jars = useJars(!!me.data?.mono_client_id);
  const active = (jars.data ?? []).filter((j) => j.is_active);
  if (!active.length) return null;

  return (
    <Animated.View entering={FadeIn.duration(APPEAR_MS)}>
      <Glass contentStyle={styles.card}>
        <Text variant="labelCaps" tone="ghost">
          Банки
        </Text>
        {active.map((j, i) => (
          <Fragment key={j.id}>
            {i > 0 && <View style={[styles.divider, { backgroundColor: withAlpha(c.shade, 0.07) }]} />}
            <JarRow jar={j} onPress={() => openJar(j.id)} />
          </Fragment>
        ))}
      </Glass>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  // same as the budgets card above it
  card: { paddingTop: 12, paddingHorizontal: 16, paddingBottom: 4 },
  divider: { height: 1 },
});
