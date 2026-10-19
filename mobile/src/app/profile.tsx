import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet } from 'react-native';

import { signOut } from '@/api/auth';
import { goBack } from '@/lib/nav';
import { lockEnabled } from '@/lib/security';
import { useTheme } from '@/theme';
import { THEME_LABELS, useThemePref } from '@/theme/preference';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Icon } from '@/ui/icons/Icon';
import { ProfileCard } from '@/ui/ProfileCard';
import { Screen } from '@/ui/Screen';
import { SettingRow } from '@/ui/SettingRow';
import { Text } from '@/ui/Text';

export default function ProfileScreen() {
  const { c } = useTheme();
  const theme = useThemePref();
  const lock = lockEnabled.useValue();
  const [busy, setBusy] = useState(false);

  return (
    <Screen background="accent">
      <Header
        title="Профіль"
        left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
      />

      <ProfileCard />

      {/* Figma: 4 16 4 16 */}
      <Glass contentStyle={styles.settings}>
        <SettingRow icon="sun" label="Тема" value={THEME_LABELS[theme]} onPress={() => router.push('/theme')} />
        <SettingRow icon="card" label="Картки" value="Порядок" onPress={() => router.push('/cards')} />
        <SettingRow
          icon="lock"
          label="Безпека"
          value={lock ? 'Код' : undefined}
          onPress={() => router.push('/security')}
        />
      </Glass>

      <Pressable
        accessibilityRole="button"
        disabled={busy}
        onPress={() => {
          setBusy(true);
          signOut();
        }}
        style={({ pressed }) => pressed && styles.pressed}
      >
        {/* plain glass with a red label: a red tint over the backdrop turns muddy */}
        <Glass radius={17} contentStyle={styles.logout}>
          {busy ? (
            <ActivityIndicator color={c.danger} />
          ) : (
            <>
              <Icon name="logout" size={17} color={c.danger} weight={1.9} />
              <Text variant="bodyStrong" tone="danger" style={styles.logoutLabel}>
                Вийти з акаунта
              </Text>
            </>
          )}
        </Glass>
      </Pressable>

    </Screen>
  );
}

const styles = StyleSheet.create({
  settings: { paddingVertical: 4, paddingHorizontal: 16 },
  logout: {
    height: 48,
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoutLabel: { fontSize: 14 },
  pressed: { opacity: 0.6 },
});
