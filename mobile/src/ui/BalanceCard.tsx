import { Pressable, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';

import { currencyCode, formatMoney, UAH } from '@/lib/money';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { cardLook } from '@/ui/cardLook';
import { Text } from '@/ui/Text';

type Props = {
  label?: string;
  balance?: number;
  currency?: number;
  // account name, e.g. «Чорна»
  account?: string;
  // last digits of the card number, like on the plastic
  pan?: string;
  // monobank card type: the plate is drawn like that card
  cardType?: string;
  hidden?: boolean;
  // tapping the balance hides or shows it
  onToggleHidden?: () => void;
  // holding the card opens the card order
  onLongPress?: () => void;
  style?: StyleProp<ViewStyle>;
  // a fact about the account under the balance, e.g. the credit limit
  detail?: { label: string; value: string };
};

const HIDDEN = '••••••';
// text on light plates (the white card) stays dark in both themes
const PLATE_INK = '#1A1714';

export function BalanceCard({
  label = 'Баланс картки',
  balance,
  currency = UAH,
  account,
  pan,
  cardType,
  hidden = false,
  onToggleHidden,
  onLongPress,
  detail,
  style,
}: Props) {
  const { c, dark } = useTheme();
  const look = cardLook(cardType, currency, c, dark);
  // translucent layers of the plate's own ink: white on dark plates, dark on light ones
  const soft = (a: number) => withAlpha(look.light ? PLATE_INK : c.white, a);
  const ink = look.light ? PLATE_INK : c.cream;
  const accent = look.light ? '#2D3E8C' : c.accentOnDark;

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
          <Text variant="labelCaps" style={[styles.label, { color: soft(0.55) }]}>
            {label}
          </Text>
          {/* the symbol next to the amount is enough for hryvnia, other currencies get their code */}
          {currency !== UAH ? (
            <View style={[styles.badge, { backgroundColor: soft(0.1) }]}>
              <Text variant="rowCaption" style={[styles.badgeText, { color: soft(0.7) }]}>
                {currencyCode(currency)}
              </Text>
            </View>
          ) : null}
        </View>
        {balance === undefined ? (
          <View style={styles.amountSlot}>
            <View style={[styles.placeholder, { backgroundColor: soft(0.1) }]} />
          </View>
        ) : (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={hidden ? 'Баланс приховано' : formatMoney(balance, currency)}
            accessibilityHint={hidden ? 'Показати баланс' : 'Сховати баланс'}
            onPress={onToggleHidden}
            onLongPress={onLongPress}
            delayLongPress={380}
            style={styles.amountTap}
          >
            <Animated.View key={hidden ? 'hidden' : 'shown'} entering={FadeIn.duration(180)} style={styles.amountRow}>
              <Text maxFontSizeMultiplier={1.3} style={[styles.amount, { color: ink }, hidden && styles.dots]}>
                {hidden ? HIDDEN : formatMoney(balance, currency)}
              </Text>
              {hidden ? (
                <Text variant="rowCaption" style={[styles.hint, { color: soft(0.45) }]}>
                  Торкнись, щоб показати
                </Text>
              ) : null}
            </Animated.View>
          </Pressable>
        )}

        <View style={styles.bottom}>
          {/* who the card is, bottom left like on the plastic */}
          <View style={styles.identity}>
            {look.motif ? (
              <View style={styles.motif}>
                <View style={[styles.dot, { backgroundColor: c.category.plum }]} />
                <View style={[styles.dash, { backgroundColor: soft(0.3) }]} />
              </View>
            ) : null}
            <Text variant="bodyStrong" numberOfLines={1} style={[styles.accountName, { color: soft(0.8) }]}>
              {account}
            </Text>
            {pan ? (
              <Text variant="rowCaption" style={[styles.pan, { color: soft(0.45) }]}>
                •• {pan}
              </Text>
            ) : null}
          </View>
          {detail ? (
            <Text
              variant="rowCaption"
              numberOfLines={1}
              accessibilityLabel={`${detail.label}: ${hidden ? 'приховано' : detail.value}`}
              style={[styles.detail, { color: soft(0.5) }]}
            >
              {detail.label}{' '}
              <Text variant="rowCaption" style={[styles.detailValue, { color: accent }]}>
                {hidden ? HIDDEN : detail.value}
              </Text>
            </Text>
          ) : null}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 26, borderCurve: 'continuous', paddingVertical: 15, paddingHorizontal: 17, overflow: 'hidden' },
  underlay: { position: 'absolute', top: 1, left: 1, right: 1, bottom: 1, borderRadius: 25, borderCurve: 'continuous' },
  held: { transform: [{ scale: 0.985 }] },
  stripe: { position: 'absolute', left: 0, top: 0, bottom: 0, width: 6 },
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 20 },
  label: { letterSpacing: 0.69 },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  badgeText: { fontSize: 11.5, letterSpacing: 0.6, fontVariant: ['tabular-nums'] },
  // the balance is the card's one big thing
  amount: { ...TEXT.amountXl, fontSize: 32, lineHeight: 38, letterSpacing: -0.8 },
  dots: { letterSpacing: -2 },
  amountTap: { alignSelf: 'flex-start', marginTop: 2 },
  // the hint sits by the dots, so hiding doesn't change the card's height
  amountRow: { flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 38 },
  hint: { fontSize: 12 },
  amountSlot: { height: 38, marginTop: 2, justifyContent: 'center' },
  placeholder: { width: 180, height: 28, borderRadius: 9 },
  bottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginTop: 14 },
  identity: { flexShrink: 1, flexDirection: 'row', alignItems: 'center', gap: 8 },
  accountName: { fontSize: 14, lineHeight: 19, flexShrink: 1 },
  pan: { letterSpacing: 0.6, fontVariant: ['tabular-nums'] },
  detail: { flexShrink: 0 },
  detailValue: { fontVariant: ['tabular-nums'] },
  motif: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  dash: { width: 20, height: 7, borderRadius: 3.5 },
});
