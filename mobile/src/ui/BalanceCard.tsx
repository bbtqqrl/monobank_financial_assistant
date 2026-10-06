import { Pressable, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';

import { formatMoney, UAH } from '@/lib/money';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { Icon } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  label?: string;
  balance?: number;
  currency?: number;
  account?: string;
  hidden?: boolean;
  onToggleHidden?: () => void;
  style?: StyleProp<ViewStyle>;
  // spendings this month
  spent?: string;
};

const HIDDEN = '••••••';

export function BalanceCard({
  label = 'Баланс картки',
  balance,
  currency = UAH,
  account,
  hidden = false,
  onToggleHidden,
  spent,
  style,
}: Props) {
  const { c } = useTheme();
  const white = (a: number) => withAlpha(c.white, a);

  const background = [
    `radial-gradient(120% 100% at 88% 4%, ${withAlpha(c.accent, 0.55)} 0%, ${withAlpha(c.accent, 0)} 58%)`,
    `radial-gradient(90% 80% at 4% 100%, rgba(196, 124, 86, 0.34) 0%, rgba(196, 124, 86, 0) 62%)`,
    `linear-gradient(152deg, ${c.cardA} 0%, ${c.cardB} 100%)`,
  ].join(', ');

  return (
    <View
      style={[
        styles.card,
        { experimental_backgroundImage: background, boxShadow: `0 20px 44px -20px ${withAlpha(c.shadow, 0.66)}` },
        style,
      ]}
    >
      <View style={styles.top}>
        <View style={styles.balance}>
          <Text variant="labelCaps" style={[styles.label, { color: white(0.55) }]}>
            {label}
          </Text>
          {balance === undefined ? (
            <View style={styles.amountSlot}>
              <View style={[styles.placeholder, { backgroundColor: white(0.1) }]} />
            </View>
          ) : (
            <Animated.Text
              key={hidden ? 'hidden' : 'shown'}
              entering={FadeIn.duration(180)}
              accessibilityLabel={hidden ? 'Баланс приховано' : undefined}
              maxFontSizeMultiplier={1.3}
              style={[TEXT.amountXl, { color: c.cream }]}
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
            { backgroundColor: white(pressed ? 0.16 : 0.1), borderColor: white(0.14) },
          ]}
        >
          <Icon name={hidden ? 'eyeOff' : 'eye'} size={18} color={c.onCard} weight={1.6} />
        </Pressable>
      </View>

      <View style={styles.bottom}>
        {spent ? (
          <View
            accessible
            accessibilityLabel={hidden ? 'Витрати приховано' : `Витрати: ${spent}`}
            style={[styles.trend, { backgroundColor: white(0.1), borderColor: white(0.12) }]}
          >
            <Icon name="arrowDown" size={13} color={c.accentOnDark} weight={2.2} />
            <Text variant="link" numberOfLines={1} style={[styles.num, { color: c.accentOnDark }]}>
              {hidden ? HIDDEN : spent}
            </Text>
          </View>
        ) : (
          <View />
        )}
        <Text variant="rowCaption" numberOfLines={1} style={[styles.account, { color: white(0.45) }]}>
          {account}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 26, padding: 17 },
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
  account: { flexShrink: 1, letterSpacing: 0.48, fontVariant: ['tabular-nums'] },
});
