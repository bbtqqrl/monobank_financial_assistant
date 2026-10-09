import type { ReactNode } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import Animated from 'react-native-reanimated';

import { accountName, ownBalance, type Account } from '@/api/accounts';
import { FONT } from '@/lib/fonts';
import { tap } from '@/lib/haptics';
import { formatMoney } from '@/lib/money';
import { useTheme, withAlpha } from '@/theme';
import { CardArt } from '@/ui/CardArt';
import { Glass } from '@/ui/Glass';
import { Icon } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';
import { useSelectRing } from '@/ui/useSelectRing';

type Props = {
  accounts: Account[];
  // null is cash
  value: number | null;
  onChange: (id: number | null) => void;
};

const ART = 52;

function Tile({ selected, label, onPress, art, pan, name, sub }: {
  selected: boolean;
  label: string;
  onPress: () => void;
  art: ReactNode;
  pan?: string;
  name: string;
  sub: string;
}) {
  const { c } = useTheme();
  const ring = useSelectRing(selected);
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ checked: selected }}
      accessibilityLabel={label}
      onPress={() => {
        if (selected) return;
        tap();
        onPress();
      }}
      style={({ pressed }) => pressed && styles.pressed}
    >
      <View>
        <Animated.View pointerEvents="none" style={[styles.ring, { borderColor: c.accent }, ring]} />
        <Glass radius={18} contentStyle={styles.tile}>
          <View style={styles.top}>
            {art}
            {pan ? (
              <Text tone="ghost" style={styles.pan}>
                •• {pan}
              </Text>
            ) : null}
          </View>
          <View>
            <Text tone="muted" style={styles.name} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.85}>
              {name}
            </Text>
            <Text style={styles.sub} numberOfLines={1}>
              {sub}
            </Text>
          </View>
        </Glass>
      </View>
    </Pressable>
  );
}

// Where the money was: cash, or one of the cards as the bank draws them
export function AccountTiles({ accounts, value, onChange }: Props) {
  const { c } = useTheme();

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
      style={styles.scroll}
      contentContainerStyle={styles.row}
    >
      <Tile
        selected={value === null}
        label="Готівка"
        onPress={() => onChange(null)}
        art={
          <View style={[styles.cash, { backgroundColor: withAlpha(c.category.green, 0.16) }]}>
            <Icon name="cash" size={20} color={c.category.green} weight={1.8} />
          </View>
        }
        name="Без картки"
        sub="Готівка"
      />
      {accounts.map((a) => {
        const pan = a.masked_pan?.slice(-4);
        return (
          <Tile
            key={a.id}
            selected={value === a.id}
            label={`${accountName(a)}${pan ? ` ${pan}` : ''}`}
            onPress={() => onChange(a.id)}
            art={<CardArt type={a.account_type} currency={a.currency_code} width={ART} />}
            pan={pan}
            name={accountName(a)}
            sub={formatMoney(ownBalance(a), a.currency_code, { cents: false })}
          />
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // runs under the sheet's side padding; the vertical room is for the shadow and ring
  scroll: { marginHorizontal: -20, marginTop: -10, marginBottom: -26 },
  row: { paddingHorizontal: 20, paddingTop: 10, paddingBottom: 26, gap: 10 },
  pressed: { opacity: 0.7 },
  // a 2pt ring hugging the tile's corners
  ring: { position: 'absolute', top: -3, left: -3, right: -3, bottom: -3, borderWidth: 2, borderRadius: 21 },
  tile: { width: 132, height: 104, padding: 12, justifyContent: 'space-between' },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cash: { width: ART, height: Math.round(ART * 0.64), borderRadius: 7, alignItems: 'center', justifyContent: 'center' },
  pan: { fontFamily: FONT.ui.medium, fontSize: 11.5, fontVariant: ['tabular-nums'] },
  name: { fontFamily: FONT.ui.medium, fontSize: 12 },
  sub: { fontFamily: FONT.ui.semiBold, fontSize: 14.5, fontVariant: ['tabular-nums'] },
});
