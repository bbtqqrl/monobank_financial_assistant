import { Stack } from 'expo-router';

import { useTheme } from '@/theme';

// screens declared below would otherwise come first, and the tab would open
// on a sheet whenever it mounts without a URL (e.g. after signing in)
export const unstable_settings = { initialRouteName: 'index' };

// Overview has its own stack so the transactions list opens inside the tab
// and keeps the tab bar, as in the design.
export default function OverviewLayout() {
  const { c } = useTheme();
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.bg } }}>
      <Stack.Screen name="index" />
      <Stack.Screen
        name="period"
        options={{
          presentation: 'formSheet',
          sheetAllowedDetents: 'fitToContents',
          sheetGrabberVisible: true,
          sheetCornerRadius: 28,
          // let the iOS sheet material show through
          contentStyle: { backgroundColor: 'transparent' },
        }}
      />
      <Stack.Screen
        name="category"
        options={{
          presentation: 'formSheet',
          // a long list: opens tall, can be pulled up to full height
          sheetAllowedDetents: [0.75, 1],
          sheetGrabberVisible: true,
          sheetCornerRadius: 28,
          contentStyle: { backgroundColor: 'transparent' },
        }}
      />
    </Stack>
  );
}
