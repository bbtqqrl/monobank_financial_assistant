import { Pressable, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';

import { formatMoney, UAH } from '@/lib/money';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { cardLook } from '@/ui/cardLook';
import { Icon } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  label?: string;
  balance?: number;
  currency?: number;
  account?: string;
  // monobank card type: the plate is drawn like that card
  cardType?: string;
  hidden?: boolean;
  onToggleHidden?: () => void;
  // holding the card opens the card order
  onLongPress?: () => void;
  style?: StyleProp<ViewStyle>;
  // spendings this month
  spent?: string;
};

const HIDDEN = '••••••';
// text on light plates (the white card) stays dark in both themes
const PLATE_INK = '#1A1714';

export function BalanceCard({
  label = 'Баланс картки',
  balance,
  currency = UAH,
  account,
  cardType,
  hidden = false,
  onToggleHidden,
  onLongPress,
  spent,
  style,
}: Props) {
  const { c, dark } = useTheme();
  const look = cardLook(cardType, currency, c, dark);
  // translucent layers of the plate's own ink: white on dark plates, dark on light ones
  const soft = (a: number) => withAlpha(look.light ? PLATE_INK : c.white, a);
  const ink = look.light ? PLATE_INK : c.cream;
  const accent = look.light ? '#2D3E8C' : c.accentOnDark;
  const icon = look.light ? '#3A322B' : c.onCard;

  // Depth: a contact shadow plus a glow in the card's own colour under it,
  // a gloss across the top and a little shade at the bottom.
  // The glow sits well under the card, or it shows as a line along the edge.
  const shadow = [
    `0 1px 2px ${withAlpha(c.shadow, 0.2)}`,
    `0 12px 26px -14px ${withAlpha(c.shadow, 0.55)}`,
    `0 30px 44px -24px ${withAlpha(look.tint, 0.5)}`,
  ].join(', ');
  // No border: the edge is all gradients and shadow. A translucent border isn't
  // covered by these layers and shows as a dark line on top and a light rim below.
  // The gloss is faint on the dark theme, or the plates look washed out.
  const shine = look.light ? (dark ? 0.22 : 0.6) : dark ? 0.05 : 0.12;
  const gloss = [
    `linear-gradient(118deg, rgba(255,255,255,${shine}) 0%, rgba(255,255,255,0) 46%)`,
    `linear-gradient(to bottom, rgba(0,0,0,0) 55%, rgba(0,0,0,${look.light ? 0.05 : 0.22}) 100%)`,
  ].join(', ');

  return (
    <Pressable
      onLongPress={onLongPress}
      delayLongPress={380}
      style={({ pressed }) => [pressed && onLongPress && styles.held, style]}
    >
      {/* The shadow comes from a plate of the card's own colour a hair smaller
          than the card: cast by the card itself, iOS cuts it out right at the
          edge and the light backdrop seeps through the smoothed edge pixels. */}
      <View style={[styles.underlay, { backgroundColor: look.base, boxShadow: shadow }]} />
      <View style={[styles.card, { experimental_backgroundImage: look.background }]}>
        <View pointerEvents="none" style={[StyleSheet.absoluteFill, { experimental_backgroundImage: gloss }]} />
        {look.stripe ? <View style={[styles.stripe, { backgroundColor: look.stripe }]} /> : null}
        <View style={styles.top}>
          <View style={styles.balance}>
            <Text variant="labelCaps" style={[styles.label, { color: soft(0.55) }]}>
              {label}
            </Text>
            {balance === undefined ? (
              <View style={styles.amountSlot}>
                <View style={[styles.placeholder, { backgroundColor: soft(0.1) }]} />
              </View>
            ) : (
              <Animated.Text
                key={hidden ? 'hidden' : 'shown'}
                entering={FadeIn.duration(180)}
                accessibilityLabel={hidden ? 'Баланс приховано' : undefined}
                maxFontSizeMultiplier={1.3}
                style={[TEXT.amountXl, { color: ink }]}
              >
                {hidden ? HIDDEN : formatMoney(balance, currency)}
              </Animated.Text>
            )}
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={hidden ? 'Показати баланс' : 'Сховати баланс'}
            hitSlop={8}
            onPress={onToggleHidden}
            style={({ pressed }) => [
              styles.eye,
              { backgroundColor: soft(pressed ? 0.16 : 0.1), borderColor: soft(0.14) },
            ]}
          >
            <Icon name={hidden ? 'eyeOff' : 'eye'} size={18} color={icon} weight={1.6} />
          </Pressable>
        </View>

        <View style={styles.bottom}>
          {spent ? (
            <View
              accessible
              accessibilityLabel={hidden ? 'Витрати приховано' : `Витрати: ${spent}`}
              style={[styles.trend, { backgroundColor: soft(0.1), borderColor: soft(0.12) }]}
            >
              <Icon name="arrowDown" size={13} color={accent} weight={2.2} />
              <Text variant="link" numberOfLines={1} style={[styles.num, { color: accent }]}>
                {hidden ? HIDDEN : spent}
              </Text>
            </View>
          ) : (
            <View />
          )}
          <View style={styles.accountRow}>
            {look.motif ? (
              <View style={styles.motif}>
                <View style={[styles.dot, { backgroundColor: c.category.plum }]} />
                <View style={[styles.dash, { backgroundColor: soft(0.3) }]} />
              </View>
            ) : null}
            <Text variant="rowCaption" numberOfLines={1} style={[styles.account, { color: soft(0.45) }]}>
              {account}
            </Text>
          </View>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 26, borderCurve: 'continuous', padding: 17, overflow: 'hidden' },
  underlay: { position: 'absolute', top: 1, left: 1, right: 1, bottom: 1, borderRadius: 25, borderCurve: 'continuous' },
  held: { transform: [{ scale: 0.985 }] },
  stripe: { position: 'absolute', left: 0, top: 0, bottom: 0, width: 6 },
  top: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' },
  balance: { gap: 7 },
  label: { letterSpacing: 0.69 },
  // same height as the amount line
  amountSlot: { height: TEXT.amountXl.lineHeight, justifyContent: 'center' },
  placeholder: { width: 170, height: 26, borderRadius: 8 },
  eye: {
    width: 34,
    height: 34,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginTop: 12 },
  trend: {
    flexShrink: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 6,
    paddingLeft: 8,
    paddingRight: 11,
    borderRadius: 11,
    borderWidth: 1,
  },
  num: { fontVariant: ['tabular-nums'] },
  accountRow: { flexShrink: 1, flexDirection: 'row', alignItems: 'center', gap: 8 },
  motif: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  dash: { width: 20, height: 7, borderRadius: 3.5 },
  account: { flexShrink: 1, letterSpacing: 0.48, fontVariant: ['tabular-nums'] },
});
