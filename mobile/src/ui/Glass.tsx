import { BlurView } from 'expo-blur';
import type { ReactNode } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { mixHex, useTheme, whiteAlpha, withAlpha } from '@/theme';

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
// The highlight is an inset shadow, so like in Figma it thins out along the
// rounded corners; a brighter top border would end in a hard diagonal there.
export function Glass({ radius = 24, blur = false, style, contentStyle, children }: Props) {
  const { c, dark } = useTheme();
  const white = (a: number) => withAlpha(c.white, whiteAlpha(a, dark));
  const stroke = whiteAlpha(0.82, dark);
  const highlight = whiteAlpha(0.9, dark);
  // On dark, the flowing backdrop can be bright right under a card; a thin
  // white veil would leave grey text unreadable there, so the glass is the
  // screen's own colour at half strength (with the white tint mixed in)
  const fill = dark ? withAlpha(mixHex(c.bg, c.white, 0.1), 0.53) : white(0.66);

  return (
    <View style={[{ borderRadius: radius, boxShadow: `0 14px 34px -16px ${withAlpha(c.shadow, 0.32)}` }, style]}>
      <View
        style={[styles.clip, { borderRadius: radius, boxShadow: `inset 0 1px 0 ${withAlpha(c.white, highlight)}` }]}
      >
        {blur ? <BlurView intensity={40} tint={dark ? 'dark' : 'light'} style={StyleSheet.absoluteFill} /> : null}
        <View
          style={[
            {
              flexGrow: 1,
              borderRadius: radius,
              backgroundColor: fill,
              borderWidth: 1,
              borderColor: withAlpha(c.white, stroke),
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
