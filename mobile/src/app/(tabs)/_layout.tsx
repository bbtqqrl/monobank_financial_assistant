import { Tabs } from 'expo-router';

import { FONT } from '@/lib/fonts';
import { useTheme } from '@/theme';

// TODO: custom glass tab bar
export default function TabsLayout() {
  const { c } = useTheme();
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
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
  );
}
