import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet } from 'react-native';

import { signOut } from '@/api/auth';
import { goBack } from '@/lib/nav';
import { useTheme, withAlpha } from '@/theme';
import { pickTheme } from '@/theme/pickTheme';
import { THEME_LABELS, useThemePref } from '@/theme/preference';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Icon } from '@/ui/icons/Icon';
import { Screen } from '@/ui/Screen';
import { SettingRow } from '@/ui/SettingRow';
import { Text } from '@/ui/Text';

export default function ProfileScreen() {
  const { c } = useTheme();
  const theme = useThemePref();
  const [busy, setBusy] = useState(false);

  return (
    <Screen background="accent">
      <Header
        title="Профіль"
        left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
        right={{ icon: 'gear', label: 'Налаштування' }}
      />

      {/* Figma: 4 16 4 16 */}
      <Glass contentStyle={styles.settings}>
        <SettingRow icon="sun" label="Тема" value={THEME_LABELS[theme]} onPress={() => pickTheme(theme)} />
        <SettingRow icon="card" label="Картки" value="Порядок" onPress={() => router.push('/cards')} />
      </Glass>

      <Pressable
        accessibilityRole="button"
        disabled={busy}
        onPress={() => {
          setBusy(true);
          signOut();
        }}
        style={({ pressed }) => [
          styles.logout,
          { backgroundColor: withAlpha(c.danger, 0.1), borderColor: withAlpha(c.danger, 0.22) },
          pressed && styles.pressed,
        ]}
      >
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
      </Pressable>

    </Screen>
  );
}

const styles = StyleSheet.create({
  settings: { paddingVertical: 4, paddingHorizontal: 16 },
  logout: {
    height: 48,
    borderRadius: 17,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoutLabel: { fontSize: 14 },
  pressed: { opacity: 0.6 },
});
