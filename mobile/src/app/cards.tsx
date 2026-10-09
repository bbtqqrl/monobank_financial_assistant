import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { accountName, ownBalance, sortedAccounts, useAccounts, type Account } from '@/api/accounts';
import { cardOrder, saveCardOrder } from '@/lib/cardOrder';
import { FONT } from '@/lib/fonts';
import { formatMoney } from '@/lib/money';
import { useTheme } from '@/theme';
import { Button } from '@/ui/Button';
import { CardArt } from '@/ui/CardArt';
import { Glass } from '@/ui/Glass';
import { Icon } from '@/ui/icons/Icon';
import { SheetHeader } from '@/ui/SheetHeader';
import { SortableList } from '@/ui/SortableList';
import { Text } from '@/ui/Text';

const ROW = 74;

const close = () => (router.canGoBack() ? router.back() : router.replace('/'));
const idOf = (a: Account) => a.id;

function CardRow({ account }: { account: Account }) {
  const { c } = useTheme();
  const pan = account.masked_pan?.slice(-4);
  return (
    <Glass radius={18} style={styles.glass} contentStyle={styles.row}>
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
      <Icon name="menu" size={18} color={c.ghost} weight={2} />
    </Glass>
  );
}

// Card order sheet: the balance carousel and the account pickers follow it.
// Gesture handler needs its own root inside a native sheet.
export default function CardsSheet() {
  const insets = useSafeAreaInsets();
  const accounts = useAccounts();
  const order = cardOrder.useValue();
  const list = sortedAccounts(accounts.data ?? [], order);

  return (
    <GestureHandlerRootView style={[styles.sheet, { paddingBottom: Math.max(insets.bottom, 16) }]}>
      <SheetHeader title="Картки" subtitle="Затисни картку й потягни, щоб змінити порядок" onClose={close} />
      <SortableList
        items={list}
        keyOf={idOf}
        rowHeight={ROW}
        renderRow={(account) => <CardRow account={account} />}
        onChange={(next) => saveCardOrder(next.map(idOf))}
      />
      {order ? <Button kind="secondary" label="Як у банку" onPress={() => saveCardOrder(null)} /> : null}
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  sheet: { paddingTop: 22, paddingHorizontal: 20, gap: 16 },
  // the slot is a bit taller than the card, that's the gap between them
  glass: { height: ROW - 10 },
  row: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 12 },
  text: { flex: 1, gap: 1 },
  name: { fontSize: 14.5 },
  pan: { fontVariant: ['tabular-nums'] },
  balance: { fontFamily: FONT.ui.semiBold, fontSize: 14.5, fontVariant: ['tabular-nums'] },
});
