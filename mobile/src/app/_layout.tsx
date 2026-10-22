import { QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import * as SystemUI from 'expo-system-ui';
import { useEffect, useState } from 'react';
import { StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { useSession } from '@/api/auth';
import { queryClient } from '@/api/query';
import { loadTokens } from '@/api/tokens';
import { loadCardPrefs } from '@/lib/cardOrder';
import { FONT_FILES } from '@/lib/fonts';
import { loadSecurityPrefs } from '@/lib/security';
import { useTheme, withAlpha } from '@/theme';
import { loadThemePref } from '@/theme/preference';
import { AppLock } from '@/ui/AppLock';
import { ThemeFade } from '@/ui/ThemeFade';

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
    Promise.all([loadThemePref(), loadCardPrefs(), loadSecurityPrefs()]).finally(() => setSettingsLoaded(true));
  }, []);

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  // the window under the screens shows in the rounded corners while one slides away
  useEffect(() => {
    SystemUI.setBackgroundColorAsync(c.bg).catch(() => {});
  }, [c.bg]);

  // the stack paints its container with the navigation theme's background, a light grey
  // by default, and that's what shows around a screen being swiped back
  const base = dark ? DarkTheme : DefaultTheme;
  const navTheme = { ...base, colors: { ...base.colors, background: c.bg } };

  if (!ready) return null;

  const signedIn = session === 'signedIn';
  const sheet = (detents: number[] | 'fitToContents') =>
    ({
      presentation: 'formSheet',
      sheetAllowedDetents: detents,
      sheetGrabberVisible: true,
      // clear glass would smear dark buttons under it
      contentStyle: { backgroundColor: withAlpha(c.sheet, 0.86) },
    }) as const;

  return (
    <GestureHandlerRootView style={styles.root}>
      <ThemeProvider value={navTheme}>
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
              {/* its button is top left, so it comes in from the left (and swipes back to it) */}
              <Stack.Screen name="profile" options={{ animation: 'slide_from_left' }} />
              <Stack.Screen name="security" />
              <Stack.Screen name="pin" />
              <Stack.Screen name="transaction/[id]/index" />
              <Stack.Screen name="transaction/[id]/category" options={sheet([0.75, 1])} />
              <Stack.Screen name="new/index" options={sheet([1])} />
              <Stack.Screen name="new/category" options={sheet([0.75, 1])} />
              <Stack.Screen name="cards" options={sheet('fitToContents')} />
              <Stack.Screen name="theme" options={sheet('fitToContents')} />
              <Stack.Screen name="budget/[id]" />
              <Stack.Screen name="jars" />
              <Stack.Screen name="jar/[id]" />
              {/* a new one needs the whole height, changing a limit only its content */}
              <Stack.Screen
                name="budget/index"
                options={({ route }) => sheet((route.params as { id?: string } | undefined)?.id ? 'fitToContents' : [1])}
              />
              <Stack.Screen name="budget/category" options={sheet([0.75, 1])} />
            </Stack.Protected>
            <Stack.Protected guard={!signedIn}>
              <Stack.Screen name="login" />
            </Stack.Protected>
          </Stack>
          {signedIn ? <AppLock /> : null}
          <ThemeFade />
        </QueryClientProvider>
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
