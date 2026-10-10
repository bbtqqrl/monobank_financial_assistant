import { QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { useSession } from '@/api/auth';
import { queryClient } from '@/api/query';
import { loadTokens } from '@/api/tokens';
import { loadCardPrefs } from '@/lib/cardOrder';
import { FONT_FILES } from '@/lib/fonts';
import { useTheme, withAlpha } from '@/theme';
import { loadThemePref } from '@/theme/preference';

// keep the splash until fonts, saved settings and the saved session are ready
SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const [loaded, error] = useFonts(FONT_FILES);
  const session = useSession();
  const { dark, c } = useTheme();
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const ready = (loaded || error) && settingsLoaded && session !== 'loading';

  useEffect(() => {
    loadTokens();
    Promise.all([loadThemePref(), loadCardPrefs()]).finally(() => setSettingsLoaded(true));
  }, []);

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  if (!ready) return null;

  const signedIn = session === 'signedIn';
  const sheet = (detents: number[] | 'fitToContents') =>
    ({
      presentation: 'formSheet',
      sheetAllowedDetents: detents,
      sheetGrabberVisible: true,
      sheetCornerRadius: 28,
      // clear glass would smear dark buttons under it
      contentStyle: { backgroundColor: withAlpha(c.sheet, 0.86) },
    }) as const;

  return (
    <GestureHandlerRootView style={styles.root}>
      <QueryClientProvider client={queryClient}>
        <StatusBar style={dark ? 'light' : 'dark'} />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: c.bg },
          }}
        >
          <Stack.Protected guard={signedIn}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="profile" />
            <Stack.Screen name="transaction/[id]/index" />
            <Stack.Screen name="transaction/[id]/category" options={sheet([0.75, 1])} />
            <Stack.Screen name="new/index" options={sheet([1])} />
            <Stack.Screen name="new/category" options={sheet([0.75, 1])} />
            <Stack.Screen name="cards" options={sheet('fitToContents')} />
          </Stack.Protected>
          <Stack.Protected guard={!signedIn}>
            <Stack.Screen name="login" />
          </Stack.Protected>
        </Stack>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
