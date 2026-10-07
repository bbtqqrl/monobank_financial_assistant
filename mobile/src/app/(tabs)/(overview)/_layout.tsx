import { Stack } from 'expo-router';

import { useTheme } from '@/theme';

// Overview has its own stack so the transactions list opens inside the tab
// and keeps the tab bar, as in the design.
export default function OverviewLayout() {
  const { c } = useTheme();
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.bg } }}>
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
    </Stack>
  );
}
