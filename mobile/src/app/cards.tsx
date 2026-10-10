import { Pressable, StyleSheet, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { accountName, ownBalance, sortedAccounts, useAccounts, type Account } from '@/api/accounts';
import { cardOrder, hiddenCards, resetCards, saveCardOrder, setCardHidden } from '@/lib/cardOrder';
import { FONT } from '@/lib/fonts';
import { formatMoney } from '@/lib/money';
import { tap } from '@/lib/haptics';
import { useTheme, withAlpha } from '@/theme';
import { Button } from '@/ui/Button';
import { CardArt } from '@/ui/CardArt';
import { Glass } from '@/ui/Glass';
import { Icon } from '@/ui/icons/Icon';
import { SheetHeader } from '@/ui/SheetHeader';
import { SortableList } from '@/ui/SortableList';
import { Text } from '@/ui/Text';

const ROW = 74;

const idOf = (a: Account) => a.id;

function CardRow({ account, hidden, canHide }: { account: Account; hidden: boolean; canHide: boolean }) {
  const { c } = useTheme();
  const pan = account.masked_pan?.slice(-4);
  // the last card shown can't go, the Overview would be left empty
  const locked = !hidden && !canHide;
  return (
    <Glass radius={18} style={styles.glass} contentStyle={styles.row}>
      <View style={[styles.card, hidden && styles.dimmed]}>
        <CardArt type={account.account_type} currency={account.currency_code} width={50} />
        <View style={styles.text}>
          <Text variant="bodyStrong" numberOfLines={1} style={styles.name}>
            {accountName(account)}
          </Text>
          {pan ? (
            <Text variant="rowCaption" tone="faint" style={styles.pan}>
              •• {pan}
            </Text>
          ) : null}
        </View>
        <Text style={styles.balance}>{formatMoney(ownBalance(account), account.currency_code, { cents: false })}</Text>
      </View>
      <Pressable
        accessibilityRole="switch"
        accessibilityLabel={`Показувати на Огляді: ${accountName(account)}${pan ? ` ${pan}` : ''}`}
        accessibilityState={{ checked: !hidden, disabled: locked }}
        disabled={locked}
        hitSlop={6}
        onPress={() => {
          tap();
          setCardHidden(account.id, !hidden);
        }}
        style={({ pressed }) => [
          styles.eye,
          { backgroundColor: withAlpha(c.shade, 0.06) },
          locked && styles.dimmed,
          pressed && styles.pressed,
        ]}
      >
        <Icon name={hidden ? 'eyeOff' : 'eye'} size={17} color={hidden ? c.ghost : c.inkSoft} weight={1.8} />
      </Pressable>
      <Icon name="menu" size={18} color={c.ghost} weight={2} />
    </Glass>
  );
}

// Card order sheet: the balance carousel and the account pickers follow it,
// and leave out the cards hidden here.
// Gesture handler needs its own root inside a native sheet.
export default function CardsSheet() {
  const insets = useSafeAreaInsets();
  const accounts = useAccounts();
  const order = cardOrder.useValue();
  const hidden = hiddenCards.useValue();
  const list = sortedAccounts(accounts.data ?? [], order);
  const shown = list.filter((a) => !hidden.includes(a.id)).length;

  return (
    <GestureHandlerRootView style={[styles.sheet, { paddingBottom: Math.max(insets.bottom, 16) }]}>
      <SheetHeader title="Картки" subtitle={'Затисни картку й потягни, щоб змінити порядок.\nОко ховає її з Огляду'} />
      <SortableList
        items={list}
        keyOf={idOf}
        rowHeight={ROW}
        renderRow={(account) => <CardRow account={account} hidden={hidden.includes(account.id)} canHide={shown > 1} />}
        onChange={(next) => saveCardOrder(next.map(idOf))}
      />
      {order || hidden.length > 0 ? <Button kind="secondary" label="Як у банку" onPress={resetCards} /> : null}
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  sheet: { paddingTop: 22, paddingHorizontal: 20, gap: 16 },
  // the slot is a bit taller than the card, that's the gap between them
  glass: { height: ROW - 10 },
  row: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 12 },
  card: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 12 },
  dimmed: { opacity: 0.4 },
  eye: { width: 32, height: 32, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  pressed: { opacity: 0.6 },
  text: { flex: 1, gap: 1 },
  name: { fontSize: 14.5 },
  pan: { fontVariant: ['tabular-nums'] },
  balance: { fontFamily: FONT.ui.semiBold, fontSize: 14.5, fontVariant: ['tabular-nums'] },
});
