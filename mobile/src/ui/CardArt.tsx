import { StyleSheet, View } from 'react-native';

import { useTheme, withAlpha } from '@/theme';
import { cardLook } from '@/ui/cardLook';

type Props = {
  // monobank card type: black, white, diia, madeInUkraine…
  type: string;
  currency: number;
  width?: number;
};

// An account's card drawn small, the same look as its balance plate
export function CardArt({ type, currency, width = 56 }: Props) {
  const { c, dark } = useTheme();
  const look = cardLook(type, currency, c, dark);
  const k = width / 56;

  return (
    <View
      style={[
        styles.card,
        {
          width,
          height: Math.round(width * 0.64),
          borderRadius: 7 * k,
          experimental_backgroundImage: look.background,
          boxShadow: `0 ${2 * k}px ${6 * k}px ${withAlpha(c.shadow, 0.28)}`,
          borderColor: look.border ?? withAlpha(c.white, 0.22),
        },
      ]}
    >
      {look.stripe ? <View style={[styles.stripe, { width: 3 * k, backgroundColor: look.stripe }]} /> : null}
      {look.motif ? (
        <View style={[styles.motif, { left: 6 * k, bottom: 6 * k, gap: 2.5 * k }]}>
          <View style={{ width: 5 * k, height: 5 * k, borderRadius: 2.5 * k, backgroundColor: c.category.plum }} />
          <View
            style={{ width: 13 * k, height: 4.5 * k, borderRadius: 2.25 * k, backgroundColor: withAlpha(c.white, 0.32) }}
          />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { overflow: 'hidden', borderWidth: StyleSheet.hairlineWidth, borderCurve: 'continuous' },
  stripe: { position: 'absolute', left: 0, top: 0, bottom: 0 },
  motif: { position: 'absolute', flexDirection: 'row', alignItems: 'center' },
});
