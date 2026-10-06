import { Link } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

import { signOut } from '@/api/auth';
import { goBack } from '@/lib/nav';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { pickTheme } from '@/theme/pickTheme';
import { THEME_LABELS, useThemePref } from '@/theme/preference';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Icon } from '@/ui/icons/Icon';
import { Screen } from '@/ui/Screen';
import { SettingRow } from '@/ui/SettingRow';
import { Text } from '@/ui/Text';

// TODO: dev shortcuts, remove before release
const DEV_LINKS = [
  { label: 'Перевірки', href: '/dev/smoke' },
  { label: 'UI kit', href: '/dev/kit' },
] as const;

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

      {__DEV__ && (
        <View style={styles.dev}>
          <Text variant="labelCaps" tone="ghost">
            Розробка
          </Text>
          {DEV_LINKS.map((l) => (
            <Link key={l.label} href={l.href} style={[TEXT.bodyStrong, { color: c.accentText }]}>
              {l.label} →
            </Link>
          ))}
        </View>
      )}
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
  dev: { paddingTop: 24, gap: 12 },
});
