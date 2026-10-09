import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

import { FONT } from '@/lib/fonts';
import { tap } from '@/lib/haptics';
import { useTheme, withAlpha } from '@/theme';
import { Text } from '@/ui/Text';

type Option<K extends string> = { key: K; label: string; tint?: string };

type Props<K extends string> = {
  options: Option<K>[];
  value: K;
  onChange: (key: K) => void;
};

const SLIDE = { duration: 220, easing: Easing.out(Easing.cubic) };

// A few choices in one capsule; a raised thumb slides under the picked one
export function Segmented<K extends string>({ options, value, onChange }: Props<K>) {
  const { c, dark } = useTheme();
  const [layouts, setLayouts] = useState<Partial<Record<K, { x: number; width: number }>>>({});
  const x = useSharedValue(0);
  const width = useSharedValue(0);
  const target = layouts[value];

  useEffect(() => {
    if (!target) return;
    // the first placement snaps, later ones slide
    if (width.get() === 0) {
      x.set(target.x);
      width.set(target.width);
    } else {
      x.set(withTiming(target.x, SLIDE));
      width.set(withTiming(target.width, SLIDE));
    }
  }, [target, x, width]);

  const thumb = useAnimatedStyle(() => ({
    left: x.get(),
    width: width.get(),
    opacity: width.get() > 0 ? 1 : 0,
  }));

  return (
    <View accessibilityRole="tablist" style={[styles.track, { backgroundColor: withAlpha(c.shade, dark ? 0.24 : 0.07) }]}>
      <Animated.View
        style={[
          styles.thumb,
          {
            // the usual glass mapping for dark is too faint to read as raised
            backgroundColor: withAlpha(c.white, dark ? 0.16 : 0.95),
            boxShadow: `0 4px 12px -6px ${withAlpha(c.shadow, 0.55)}`,
          },
          thumb,
        ]}
      />
      {options.map((o) => {
        const on = o.key === value;
        return (
          <Pressable
            key={o.key}
            accessibilityRole="tab"
            accessibilityState={{ selected: on }}
            onPress={() => {
              if (on) return;
              tap();
              onChange(o.key);
            }}
            onLayout={(e) => {
              const { x: left, width: w } = e.nativeEvent.layout;
              setLayouts((prev) => ({ ...prev, [o.key]: { x: left, width: w } }));
            }}
            style={styles.segment}
          >
            {/* a tint is too dim on the dark thumb, plain ink reads better there */}
            <Text style={[styles.label, on && styles.labelOn, { color: on ? (dark ? c.ink : (o.tint ?? c.ink)) : c.muted }]}>
              {o.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  track: { flexDirection: 'row', alignSelf: 'center', padding: 3, borderRadius: 14 },
  thumb: { position: 'absolute', top: 3, bottom: 3, borderRadius: 11 },
  segment: { height: 32, paddingHorizontal: 18, justifyContent: 'center' },
  label: { fontFamily: FONT.ui.medium, fontSize: 13.5 },
  labelOn: { fontFamily: FONT.ui.semiBold },
});
