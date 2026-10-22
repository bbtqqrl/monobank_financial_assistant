import { InputAccessoryView, Keyboard, Platform, Pressable, StyleSheet, View } from 'react-native';

import { tap } from '@/lib/haptics';
import { useTheme, withAlpha } from '@/theme';
import { Text } from '@/ui/Text';

// pass as inputAccessoryViewID to the fields that should get the bar
export const KEYBOARD_DONE_ID = 'keyboard-done';

// The number pad has no return key: a thin bar over it with «Готово», so the
// keyboard can be put away without knowing to swipe the screen
export function KeyboardDone() {
  const { c } = useTheme();
  if (Platform.OS !== 'ios') return null;

  return (
    <InputAccessoryView nativeID={KEYBOARD_DONE_ID}>
      <View style={[styles.bar, { borderTopColor: withAlpha(c.shade, 0.08), backgroundColor: withAlpha(c.sheet, 0.94) }]}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Сховати клавіатуру"
          hitSlop={10}
          onPress={() => {
            tap();
            Keyboard.dismiss();
          }}
          style={({ pressed }) => pressed && styles.pressed}
        >
          <Text variant="bodyStrong" tone="accentText">
            Готово
          </Text>
        </Pressable>
      </View>
    </InputAccessoryView>
  );
}

const styles = StyleSheet.create({
  bar: {
    height: 44,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  pressed: { opacity: 0.6 },
});
