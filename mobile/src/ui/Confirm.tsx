import { Pressable, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';

import { tap } from '@/lib/haptics';
import { useTheme, whiteAlpha, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Text } from '@/ui/Text';

type Props = {
  question: string;
  onYes: () => void;
  onClose: () => void;
  // where the card sits on the screen, next to the button that asked
  style: StyleProp<ViewStyle>;
};

const IN = FadeIn.duration(160);
const OUT = FadeOut.duration(120);

// The app's own yes/no: a small glass card by the button that asked, a tap
// anywhere else is a no. Drawn over the screen, not as a system alert.
export function Confirm({ question, onYes, onClose, style }: Props) {
  const { c, dark } = useTheme();
  const answer = (yes: boolean) => {
    tap();
    onClose();
    if (yes) onYes();
  };

  return (
    // the whole layer fades in and out together, so it leaves as softly as it came
    <Animated.View entering={IN} exiting={OUT} style={StyleSheet.absoluteFill}>
      {/* a faint veil over the rest: the question is what matters now */}
      <Pressable
        style={[StyleSheet.absoluteFill, { backgroundColor: withAlpha(c.shade, 0.12) }]}
        onPress={() => answer(false)}
        accessibilityLabel="Ні"
      />
      <View style={[styles.card, style]}>
        <Glass radius={20} blur contentStyle={styles.content}>
          <Text variant="rowTitle" style={styles.question}>
            {question}
          </Text>
          <View style={styles.row}>
            <Pressable
              accessibilityRole="button"
              onPress={() => answer(false)}
              style={({ pressed }) => [
                styles.button,
                { backgroundColor: withAlpha(c.white, whiteAlpha(0.6, dark)) },
                pressed && styles.pressed,
              ]}
            >
              <Text variant="bodyStrong">Ні</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={() => answer(true)}
              style={({ pressed }) => [styles.button, { backgroundColor: c.accentFill }, pressed && styles.pressed]}
            >
              <Text variant="bodyStrong" tone="onPrimary">
                Так
              </Text>
            </Pressable>
          </View>
        </Glass>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: { position: 'absolute', width: 240 },
  content: { padding: 14, gap: 12 },
  question: { textAlign: 'center' },
  row: { flexDirection: 'row', gap: 8 },
  button: {
    flex: 1,
    height: 38,
    borderRadius: 12,
    borderCurve: 'continuous',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: { opacity: 0.6 },
});
