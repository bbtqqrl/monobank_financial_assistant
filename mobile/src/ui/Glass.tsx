import { BlurView } from 'expo-blur';
import type { ReactNode } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { useTheme, whiteAlpha, withAlpha } from '@/theme';

type Props = {
  radius?: number;
  // real backdrop blur, only needed over busy backgrounds (the map)
  blur?: boolean;
  // outer box: margins, size, flex
  style?: StyleProp<ViewStyle>;
  // inner box: padding, gap, layout of children
  contentStyle?: StyleProp<ViewStyle>;
  children?: ReactNode;
};

// Figma: fill white 66%, 1px inside stroke white 82%, 1px inner top highlight
// white 90%, drop shadow 0 14 34 -16 at 32%, background blur 22.
// Stroke and highlight overlap on the top edge, so the top border gets both.
export function Glass({ radius = 24, blur = false, style, contentStyle, children }: Props) {
  const { c, dark } = useTheme();
  const white = (a: number) => withAlpha(c.white, whiteAlpha(a, dark));
  const stroke = whiteAlpha(0.82, dark);
  const highlight = whiteAlpha(0.9, dark);
  const topEdge = 1 - (1 - stroke) * (1 - highlight);

  return (
    <View style={[{ borderRadius: radius, boxShadow: `0 14px 34px -16px ${withAlpha(c.shadow, 0.32)}` }, style]}>
      <View style={[styles.clip, { borderRadius: radius }]}>
        {blur ? <BlurView intensity={40} tint={dark ? 'dark' : 'light'} style={StyleSheet.absoluteFill} /> : null}
        <View
          style={[
            {
              flexGrow: 1,
              borderRadius: radius,
              backgroundColor: white(0.66),
              borderWidth: 1,
              borderColor: withAlpha(c.white, stroke),
              borderTopColor: withAlpha(c.white, topEdge),
            },
            contentStyle,
          ]}
        >
          {children}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  clip: { overflow: 'hidden', flexGrow: 1 },
});
