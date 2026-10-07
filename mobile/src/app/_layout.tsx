import { QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';

import { useSession } from '@/api/auth';
import { queryClient } from '@/api/query';
import { loadTokens } from '@/api/tokens';
import { FONT_FILES } from '@/lib/fonts';
import { useTheme } from '@/theme';
import { loadThemePref } from '@/theme/preference';

// keep the splash until fonts, the theme choice and the saved session are ready
SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const [loaded, error] = useFonts(FONT_FILES);
  const session = useSession();
  const { dark, c } = useTheme();
  const [themeLoaded, setThemeLoaded] = useState(false);
  const ready = (loaded || error) && themeLoaded && session !== 'loading';

  useEffect(() => {
    loadTokens();
    loadThemePref().finally(() => setThemeLoaded(true));
  }, []);

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  if (!ready) return null;

  const signedIn = session === 'signedIn';

  return (
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
          <Stack.Screen name="transaction/[id]" />
        </Stack.Protected>
        <Stack.Protected guard={!signedIn}>
          <Stack.Screen name="login" />
        </Stack.Protected>
      </Stack>
    </QueryClientProvider>
  );
}
