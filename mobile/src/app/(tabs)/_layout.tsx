import { Tabs, usePathname } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { FONT } from '@/lib/fonts';
import { useTheme } from '@/theme';
import { Backdrop, type BackdropVariant } from '@/ui/Backdrop';

// One backdrop for all tabs, each tab has its own tint.
// Огляд has no spots: the map goes there.
const TAB_TINT: Record<string, BackdropVariant> = {
  '/': 'none',
  '/budgets': 'green',
  '/add': 'warm',
  '/analytics': 'warm',
  '/assistant': 'accent',
};

// TODO: custom glass tab bar
export default function TabsLayout() {
  const { c } = useTheme();
  const pathname = usePathname();

  return (
    <View style={styles.root}>
      <Backdrop variant={TAB_TINT[pathname] ?? 'warm'} />
      <Tabs
        screenOptions={{
          headerShown: false,
          animation: 'fade',
          sceneStyle: { backgroundColor: 'transparent' },
          tabBarActiveTintColor: c.ink,
          tabBarInactiveTintColor: c.ghost,
          tabBarStyle: { backgroundColor: c.sheet },
          tabBarLabelStyle: { fontFamily: FONT.ui.medium, fontSize: 11 },
          tabBarIconStyle: { display: 'none' },
        }}
      >
        <Tabs.Screen name="index" options={{ title: 'Огляд' }} />
        <Tabs.Screen name="budgets" options={{ title: 'Бюджети' }} />
        <Tabs.Screen name="add" options={{ title: 'Додати' }} />
        <Tabs.Screen name="analytics" options={{ title: 'Аналітика' }} />
        <Tabs.Screen name="assistant" options={{ title: 'Асистент' }} />
      </Tabs>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
