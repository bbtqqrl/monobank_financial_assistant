import type { ReactNode } from 'react';
import { Platform, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Backdrop, type BackdropVariant } from '@/ui/Backdrop';

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

  return (
    <View style={styles.screen}>
      <Backdrop variant={background} />
      <ScrollView
        contentInsetAdjustmentBehavior="automatic"
        contentContainerStyle={[styles.content, { paddingTop: top, gap }]}
        refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} /> : undefined}
      >
        {children}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 24 },
});
