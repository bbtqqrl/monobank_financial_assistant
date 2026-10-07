import { useState } from 'react';
import { StyleSheet, useWindowDimensions, View } from 'react-native';
import Animated, {
  Extrapolation,
  interpolate,
  useAnimatedScrollHandler,
  useAnimatedStyle,
  useSharedValue,
  type SharedValue,
} from 'react-native-reanimated';

import { useTheme } from '@/theme';
import { BalanceCard } from '@/ui/BalanceCard';

export type BalanceCardData = {
  key: string | number;
  label?: string;
  balance: number;
  currency: number;
  account: string;
  spent?: string;
};

const SIDE = 20;
// same as the side padding, so the next card stays off screen until you swipe
const GAP = SIDE;
// room for the card shadow (0 20 44 -20), the scroll view would clip it otherwise
const SHADOW = 48;

// Swipe between accounts. The row runs edge to edge so cards slide in from
// the screen edge; dots below follow the finger.
export function BalanceCarousel({ cards }: { cards: BalanceCardData[] }) {
  const { width } = useWindowDimensions();
  // TODO: remember between launches once settings are stored
  const [hidden, setHidden] = useState(false);
  const progress = useSharedValue(0);
  const cardWidth = width - SIDE * 2;
  const step = cardWidth + GAP;

  const onScroll = useAnimatedScrollHandler((e) => {
    progress.set(e.contentOffset.x / step);
  });

  const toggle = () => setHidden((h) => !h);

  if (cards.length < 2) {
    const card = cards[0];
    return <BalanceCard {...card} hidden={hidden} onToggleHidden={toggle} />;
  }

  return (
    <View>
      <Animated.ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        snapToInterval={step}
        decelerationRate="fast"
        disableIntervalMomentum
        onScroll={onScroll}
        scrollEventThrottle={16}
        style={styles.row}
        contentContainerStyle={styles.content}
      >
        {cards.map((card) => (
          <BalanceCard {...card} key={card.key} hidden={hidden} onToggleHidden={toggle} style={{ width: cardWidth }} />
        ))}
      </Animated.ScrollView>
      <View style={styles.dots}>
        {cards.map((card, i) => (
          <Dot key={card.key} index={i} progress={progress} />
        ))}
      </View>
    </View>
  );
}

function Dot({ index, progress }: { index: number; progress: SharedValue<number> }) {
  const { c } = useTheme();
  // Figma: active 16×5 at 42%, the rest 5×5 at 17%
  const style = useAnimatedStyle(() => {
    const t = interpolate(Math.abs(progress.value - index), [0, 1], [1, 0], Extrapolation.CLAMP);
    return { width: 5 + 11 * t, opacity: 0.17 + 0.25 * t };
  });
  return <Animated.View style={[styles.dot, { backgroundColor: c.shade }, style]} />;
}

const styles = StyleSheet.create({
  row: { marginHorizontal: -SIDE, marginBottom: -SHADOW },
  content: { paddingHorizontal: SIDE, paddingBottom: SHADOW, gap: GAP },
  dots: { flexDirection: 'row', justifyContent: 'center', gap: 5, marginTop: 9 },
  dot: { height: 5, borderRadius: 3 },
});
