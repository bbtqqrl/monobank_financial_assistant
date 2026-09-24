import { Tabs } from 'expo-router';
import { useColorScheme } from 'react-native';

import { FONT } from '@/lib/fonts';

// TODO: custom glass tab bar
export default function TabsLayout() {
  const dark = useColorScheme() === 'dark';
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: dark ? '#F0EDE6' : '#1A1714',
        tabBarInactiveTintColor: dark ? '#6F6B76' : '#A9A39A',
        tabBarStyle: { backgroundColor: dark ? '#1B1A20' : '#FFFFFF' },
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
