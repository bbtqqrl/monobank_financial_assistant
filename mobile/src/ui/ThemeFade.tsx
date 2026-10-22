import { StyleSheet, View } from 'react-native';
import Animated, { Easing, useSharedValue, withTiming } from 'react-native-reanimated';
import { FullWindowOverlay } from 'react-native-screens';
import { scheduleOnRN } from 'react-native-worklets';

import { themeFadeDone, themeShot } from '@/lib/themeSwitch';
import { setThemePref } from '@/theme/preference';

const FADE_MS = 380;

// The old screen over everything, sheets included, while the theme changes
// underneath; then it melts away
export function ThemeFade() {
  const shot = themeShot.useValue();
  const opacity = useSharedValue(1);
  if (!shot) return null;

  // the picture is on screen: now the theme can change under it, a frame later
  const onLoad = () => {
    opacity.set(1);
    requestAnimationFrame(() => {
      setThemePref(shot.pref);
      requestAnimationFrame(() => {
        opacity.set(
          withTiming(0, { duration: FADE_MS, easing: Easing.inOut(Easing.quad) }, (finished) => {
            if (finished) scheduleOnRN(themeFadeDone, shot.uri);
          }),
        );
      });
    });
  };

  return (
    <FullWindowOverlay>
      {/* only a picture: taps go through to the app, already in the new theme */}
      <View pointerEvents="none" style={StyleSheet.absoluteFill}>
        <Animated.Image
          key={shot.uri}
          source={{ uri: shot.uri }}
          onLoad={onLoad}
          resizeMode="cover"
          style={[StyleSheet.absoluteFill, { opacity }]}
        />
      </View>
    </FullWindowOverlay>
  );
}
