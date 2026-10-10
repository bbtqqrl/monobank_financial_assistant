import { useQueryClient } from '@tanstack/react-query';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';

import { useMe } from '@/api/auth';
import { REFRESH_FLASH, refreshAccounts, syncedRecently, useMonobankStatus } from '@/api/monobank';
import { FONT } from '@/lib/fonts';
import { failure, success, tap } from '@/lib/haptics';
import { useFlash } from '@/lib/useFlash';
import { useTheme, withAlpha, type Colors } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Icon } from '@/ui/icons/Icon';
import { SpinIcon } from '@/ui/SpinIcon';
import { Text } from '@/ui/Text';

type Line = { dot: string; title: string; caption: string };

function monobankLine(c: Colors, connected: boolean, status: ReturnType<typeof useMonobankStatus>): Line {
  if (!connected) {
    return { dot: c.ghost, title: 'monobank не підключено', caption: 'Баланс і транзакції зʼявляться після підключення' };
  }
  const title = 'monobank підключено';
  if (status.data?.live) return { dot: c.category.green, title, caption: 'Нові транзакції приходять самі' };
  if (status.data) return { dot: c.warning, title, caption: 'Нові транзакції не приходять, підключи токен ще раз' };
  if (status.isError) return { dot: c.ghost, title, caption: 'Не вдалося перевірити оновлення' };
  return { dot: c.ghost, title, caption: 'Перевіряю оновлення…' };
}

// Who is signed in and whether monobank still sends new transactions (Figma: Profile header)
export function ProfileCard() {
  const { c } = useTheme();
  const qc = useQueryClient();
  const me = useMe();
  const connected = !!me.data?.mono_client_id;
  const status = useMonobankStatus(connected);
  const line = me.data && monobankLine(c, connected, status);
  // what the sync button just did, shown for a moment in place of the status
  const [shown, flash] = useFlash();

  const sync = () => {
    if (status.isFetching) return;
    // the balances came from monobank under a minute ago, there's nothing newer
    if (syncedRecently(qc)) {
      tap();
      flash(REFRESH_FLASH.recent);
      return;
    }
    refreshAccounts(qc).then((result) => {
      (result === 'synced' ? success : failure)();
      flash(REFRESH_FLASH[result]);
    });
  };

  return (
    <Glass contentStyle={styles.card}>
      <View style={styles.user}>
        <View style={[styles.avatar, { experimental_backgroundImage: `linear-gradient(150deg, ${c.cardA}, ${c.cardB})` }]}>
          <Text style={[styles.initial, { color: c.cream }]}>{me.data?.email[0]?.toUpperCase()}</Text>
        </View>
        {me.data ? (
          <Text style={styles.email} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.8}>
            {me.data.email}
          </Text>
        ) : me.isError ? (
          <Text tone="faint">Не вдалося завантажити профіль</Text>
        ) : (
          <View style={[styles.placeholder, { backgroundColor: withAlpha(c.shade, 0.07) }]} />
        )}
      </View>

      {line ? (
        <View style={[styles.status, { borderTopColor: withAlpha(c.shade, 0.07) }]}>
          <View style={[styles.dot, { backgroundColor: line.dot, boxShadow: `0 0 0 3px ${withAlpha(line.dot, 0.16)}` }]} />
          <View style={styles.statusText}>
            <Text variant="bodyStrong">{line.title}</Text>
            <Animated.View key={shown?.text ?? 'status'} entering={FadeIn.duration(160)}>
              <Text variant="rowCaption" style={{ color: shown && !shown.ok ? c.danger : c.faint }}>
                {shown ? shown.text : line.caption}
              </Text>
            </Animated.View>
          </View>
          {connected ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Оновити баланси"
              accessibilityState={{ busy: status.isFetching }}
              hitSlop={6}
              onPress={sync}
              style={({ pressed }) => [
                styles.refresh,
                { backgroundColor: withAlpha(c.shade, 0.06) },
                pressed && styles.pressed,
              ]}
            >
              {shown ? (
                <Animated.View key="note" entering={FadeIn.duration(160)} exiting={FadeOut.duration(160)}>
                  <Icon name={shown.ok ? 'check' : 'close'} size={16} color={shown.ok ? c.category.green : c.danger} weight={2.2} />
                </Animated.View>
              ) : (
                <Animated.View key="sync" entering={FadeIn.duration(160)} exiting={FadeOut.duration(160)}>
                  <SpinIcon spinning={status.isFetching} color={c.inkSoft} />
                </Animated.View>
              )}
            </Pressable>
          ) : null}
        </View>
      ) : null}
    </Glass>
  );
}

const styles = StyleSheet.create({
  // Figma: 16
  card: { padding: 16 },
  user: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  avatar: { width: 56, height: 56, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  initial: { fontFamily: FONT.display.semiBold, fontSize: 21, lineHeight: 26 },
  email: { flex: 1, fontFamily: FONT.ui.semiBold, fontSize: 16, lineHeight: 21 },
  placeholder: { width: 160, height: 16, borderRadius: 6 },
  status: { flexDirection: 'row', alignItems: 'center', gap: 9, marginTop: 14, paddingTop: 13, borderTopWidth: 1 },
  dot: { width: 8, height: 8, borderRadius: 4, marginHorizontal: 3 },
  statusText: { flex: 1, gap: 1 },
  refresh: { width: 32, height: 32, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  pressed: { opacity: 0.6 },
});
