import type { ReactNode } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import Animated, { useSharedValue } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { usePullScroll, type PullRefresh } from '@/lib/usePullRefresh';
import type { BackdropVariant } from '@/ui/Backdrop';
import { PullIndicator, PullRefreshControl } from '@/ui/PullIndicator';
import { ScrollBackdrop } from '@/ui/ScrollBackdrop';

type Props = {
  background?: BackdropVariant;
  // space between blocks, 9 on most screens
  gap?: number;
  // pull to refresh, from usePullRefresh
  pull?: PullRefresh;
  children: ReactNode;
};

// (Figma: content starts at 58 under a 47pt status bar).
export function Screen({ background = 'warm', gap = 9, pull, children }: Props) {
  const insets = useSafeAreaInsets();
  const top = 11 + (Platform.OS === 'android' ? insets.top : 0);
  const bottom = 24 + (Platform.OS === 'android' ? insets.bottom : 0);
  // iOS starts scrolled to minus the status bar inset
  const rest = Platform.OS === 'ios' ? -insets.top : 0;
  const offset = useSharedValue(rest);
  const onScroll = usePullScroll({ offset, rest, pull });

  return (
    <View style={styles.screen}>
      <Animated.ScrollView
        onScroll={onScroll}
        scrollEventThrottle={16}
        contentInsetAdjustmentBehavior="automatic"
        contentContainerStyle={[styles.content, { paddingTop: top, paddingBottom: bottom, gap }]}
        refreshControl={pull && Platform.OS === 'android' ? <PullRefreshControl pull={pull} /> : undefined}
      >
        <ScrollBackdrop variant={background} offset={offset} />
        {pull ? <PullIndicator offset={offset} rest={rest} top={insets.top + 8} /> : null}
        {children}
      </Animated.ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingHorizontal: 20 },
});
