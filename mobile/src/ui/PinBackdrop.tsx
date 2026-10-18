import { StyleSheet, useWindowDimensions, View } from 'react-native';

import { useTheme, withAlpha } from '@/theme';
import { FlowField } from '@/ui/FlowField';

// Behind the code pad: brighter than the tabs' backdrop, an accent aura behind
// the avatar and warmer colours low down, all flowing slowly
export function PinBackdrop() {
  const { c, dark } = useTheme();
  const { width, height } = useWindowDimensions();
  const aspect = height / width;
  const k = (op: number) => op * (dark ? 1 : 0.8);

  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <FlowField
        base={c.bg}
        running
        blobs={[
          { color: c.category.taxi, opacity: k(0.3), x: 0.95, y: aspect * 0.45, r: 0.5 },
          { color: c.category.teal, opacity: k(0.42), x: 0.0, y: aspect * 0.8, r: 0.65 },
          { color: c.category.copper, opacity: k(0.38), x: 1.0, y: aspect * 0.92, r: 0.6 },
          { color: c.accent, opacity: k(0.6), x: 0.5, y: aspect * 0.2, r: 0.62 },
          { color: c.accent, opacity: k(0.2), x: 0.1, y: 0.05, r: 0.4 },
        ]}
      />
      {/* a soft darkening at the bottom keeps the keys readable over the colour */}
      <View
        style={[
          StyleSheet.absoluteFill,
          { experimental_backgroundImage: `linear-gradient(180deg, ${withAlpha(c.bg, 0)} 40%, ${withAlpha(c.bg, 0.45)} 100%)` },
        ]}
      />
    </View>
  );
}
