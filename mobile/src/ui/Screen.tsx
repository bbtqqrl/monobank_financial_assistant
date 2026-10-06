import type { ReactNode } from 'react';
import { Platform, RefreshControl, StyleSheet, View } from 'react-native';
import Animated, { useAnimatedScrollHandler, useSharedValue } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { BackdropVariant } from '@/ui/Backdrop';
import { ScrollBackdrop } from '@/ui/ScrollBackdrop';

type Props = {
  background?: BackdropVariant;
  // space between blocks, 9 on most screens
  gap?: number;
  // pull to refresh
  refreshing?: boolean;
  onRefresh?: () => void;
  children: ReactNode;
};

// (Figma: content starts at 58 under a 47pt status bar).
export function Screen({ background = 'warm', gap = 9, refreshing = false, onRefresh, children }: Props) {
  const insets = useSafeAreaInsets();
  const top = 11 + (Platform.OS === 'android' ? insets.top : 0);
  const bottom = 24 + (Platform.OS === 'android' ? insets.bottom : 0);
  // iOS starts scrolled to minus the status bar inset
  const offset = useSharedValue(Platform.OS === 'ios' ? -insets.top : 0);
  const onScroll = useAnimatedScrollHandler((e) => {
    offset.set(e.contentOffset.y);
  });

  return (
    <View style={styles.screen}>
      <Animated.ScrollView
        onScroll={onScroll}
        scrollEventThrottle={16}
        contentInsetAdjustmentBehavior="automatic"
        contentContainerStyle={[styles.content, { paddingTop: top, paddingBottom: bottom, gap }]}
        refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} /> : undefined}
      >
        <ScrollBackdrop variant={background} offset={offset} />
        {children}
      </Animated.ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingHorizontal: 20 },
});
