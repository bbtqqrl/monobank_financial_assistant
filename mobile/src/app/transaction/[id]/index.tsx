import { router, useLocalSearchParams } from 'expo-router';
import { Fragment } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, View } from 'react-native';

import { accountLabel, useAccountCurrencies, useAccounts } from '@/api/accounts';
import { ApiError } from '@/api/client';
import {
  categoryName,
  foreignPart,
  isUncategorized,
  txCurrency,
  useDeleteTransaction,
  useTransaction,
  type TransactionDetail,
} from '@/api/transactions';
import { categoryLook } from '@/lib/categories';
import { formatMoney } from '@/lib/money';
import { fullDate } from '@/lib/time';
import { goBack } from '@/lib/nav';
import { useMask } from '@/lib/privacy';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { CategoryChip } from '@/ui/CategoryChip';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Screen } from '@/ui/Screen';
import { Text } from '@/ui/Text';

// where the category came from, see category_source in the backend
function sourceLine(t: TransactionDetail): { icon: IconName; text: string; unsure?: boolean } {
  if (t.source === 'manual') return { icon: 'pencil', text: 'Додано вручну' };
  if (t.category_source === 'ai_failed' || (t.category_source !== null && isUncategorized(t))) {
    return { icon: 'sparkle', text: 'Обери категорію', unsure: true };
  }
  switch (t.category_source) {
    case 'user':
      return { icon: 'pencil', text: 'Обрано вручну' };
    case 'pair':
      return { icon: 'transfer', text: 'Переказ між своїми' };
    case 'rule':
      return { icon: 'list', text: 'За кодом MCC' };
    case 'mapping':
      return { icon: 'repeat', text: 'Як минулого разу' };
    case 'ai':
      return { icon: 'sparkle', text: 'Автоматично' };
    case 'mapping_low_confidence':
    case 'ai_low_confidence':
      return { icon: 'sparkle', text: 'Перевір категорію', unsure: true };
    default:
      return { icon: 'sparkle', text: 'Ще визначаємо' };
  }
}

function CategoryAction({ icon, label, onPress }: { icon: IconName; label: string; onPress: () => void }) {
  const { c } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.action, { backgroundColor: withAlpha(c.shade, 0.06) }, pressed && styles.pressed]}
    >
      <Icon name={icon} size={15} color={c.inkSoft} weight={2} />
      <Text variant="bodyStrong" numberOfLines={1} style={styles.actionText}>
        {label}
      </Text>
    </Pressable>
  );
}

export default function TransactionScreen() {
  const { c } = useTheme();
  const mask = useMask();
  const { id } = useLocalSearchParams<{ id: string }>();
  const tx = useTransaction(Number(id));
  const remove = useDeleteTransaction(Number(id));
  const accounts = useAccounts();
  const currencies = useAccountCurrencies();
  const t = tx.data;

  // only what was added by hand can go, the bank's own history stays
  const confirmDelete = () =>
    Alert.alert('Видалити транзакцію?', 'Її не можна буде повернути', [
      { text: 'Скасувати', style: 'cancel' },
      {
        text: 'Видалити',
        style: 'destructive',
        onPress: () =>
          remove.mutate(undefined, {
            onSuccess: goBack,
            onError: () => Alert.alert('Не вдалося видалити', 'Перевір інтернет і спробуй ще раз'),
          }),
      },
    ]);

  const header = (
    <Header
      title="Деталі транзакції"
      small
      left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
      right={
        t?.source === 'manual' ? { icon: 'dots', label: 'Видалити', weight: 2.4, onPress: confirmDelete } : undefined
      }
    />
  );

  if (!t || !currencies) {
    const notFound = tx.error instanceof ApiError && tx.error.status === 404;
    return (
      <Screen background="green">
        {header}
        {tx.isError || !Number.isInteger(Number(id)) ? (
          <Text tone="faint" style={styles.message}>
            {notFound ? 'Транзакцію не знайдено' : 'Не вдалося завантажити транзакцію'}
          </Text>
        ) : (
          <ActivityIndicator style={styles.message} />
        )}
      </Screen>
    );
  }

  const look = categoryLook(t.category?.slug, t.amount);
  const currency = txCurrency(t, currencies);
  const original = foreignPart(t, currencies);
  const income = t.amount > 0;
  const src = sourceLine(t);
  const account = accounts.data?.find((a) => a.id === t.account_id);
  const changeCategory = (scope?: 'merchant') =>
    router.push({ pathname: '/transaction/[id]/category', params: { id: String(t.id), ...(scope && { scope }) } });
  // the backend remembers the merchant: its other purchases can move along
  const forMerchant = t.source !== 'manual' && t.merchant_mapping_id !== null;
  const tint = src.unsure ? c.warning : c.accent;

  const info: [string, string][] = [];
  if (account) info.push(['Рахунок', accountLabel(account)]);
  else if (t.jar_id !== null) info.push(['Рахунок', 'Банка']);
  else if (t.source === 'manual') info.push(['Рахунок', 'Готівка']);
  if (original) info.push(['Сума покупки', mask(formatMoney(original.amount, original.currency, { sign: 'never' }))]);
  if (t.counter_name) info.push(['Отримувач', t.counter_name]);
  if (t.comment) info.push(['Коментар', t.comment]);
  if (t.mcc !== null) info.push(['MCC', String(t.mcc)]);
  // like the card balance, without the credit limit
  if (t.balance !== null) info.push(['Баланс після', mask(formatMoney(t.balance - (account?.credit_limit ?? 0), currency))]);

  return (
    <Screen background="green">
      {header}

      <View style={styles.hero}>
        <CategoryChip {...look} size={62} radius={22} />
        <Text variant="bodyStrong" style={styles.title} numberOfLines={2}>
          {t.description}
        </Text>
        <Text style={[TEXT.amountXl, styles.amount, { color: income ? c.category.green : c.ink }]}>
          {mask(formatMoney(t.amount, currency, { sign: income ? 'always' : 'auto' }))}
        </Text>
        <Text variant="rowCaption" tone="faint" style={styles.date}>
          {fullDate(t.time)}
        </Text>
      </View>

      <Glass radius={22} contentStyle={styles.category}>
        <Text variant="labelCaps" tone="ghost">
          Категорія
        </Text>
        <View style={styles.categoryRow}>
          <CategoryChip {...look} size={44} radius={15} />
          <View style={styles.categoryText}>
            <Text variant="bodyStrong" style={styles.categoryName} numberOfLines={2}>
              {categoryName(t)}
            </Text>
            <View style={[styles.badge, { backgroundColor: withAlpha(tint, 0.13) }]}>
              <Icon name={src.icon} size={11} color={tint} weight={2.2} />
              <Text variant="rowCaption" style={[styles.badgeText, { color: tint }]}>
                {src.text}
              </Text>
            </View>
          </View>
        </View>
        <View style={styles.actions}>
          <CategoryAction icon="pencil" label="Змінити" onPress={() => changeCategory()} />
          {forMerchant ? (
            <CategoryAction icon="repeat" label="Змінити для всіх" onPress={() => changeCategory('merchant')} />
          ) : null}
        </View>
      </Glass>

      {info.length > 0 && (
        <Glass radius={22} contentStyle={styles.info}>
          <Text variant="labelCaps" tone="ghost">
            Інформація
          </Text>
          {info.map(([key, value], i) => (
            <Fragment key={key}>
              {i > 0 && <View style={[styles.divider, { backgroundColor: withAlpha(c.shade, 0.07) }]} />}
              <View style={styles.infoRow}>
                <Text tone="muted">{key}</Text>
                <Text variant="bodyStrong" style={styles.infoValue}>
                  {value}
                </Text>
              </View>
            </Fragment>
          ))}
        </Glass>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  message: { paddingVertical: 40, textAlign: 'center' },
  hero: { alignItems: 'center', gap: 7, paddingTop: 2, paddingBottom: 4 },
  title: { fontSize: 16, lineHeight: 21, textAlign: 'center' },
  amount: { fontSize: 29, lineHeight: 33, letterSpacing: -0.29, fontVariant: ['tabular-nums'] },
  date: { fontSize: 12.5 },
  category: { paddingTop: 12, paddingHorizontal: 16, paddingBottom: 14, gap: 12 },
  categoryRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  categoryText: { flex: 1, gap: 6, alignItems: 'flex-start' },
  categoryName: { fontSize: 16, lineHeight: 21 },
  badge: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingVertical: 3, paddingHorizontal: 8, borderRadius: 8 },
  badgeText: { fontSize: 11.5, lineHeight: 15 },
  actions: { flexDirection: 'row', gap: 8 },
  action: {
    flex: 1,
    height: 40,
    borderRadius: 13,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    paddingHorizontal: 10,
  },
  actionText: { fontSize: 13.5, flexShrink: 1 },
  // Figma: 12 16 4 16
  info: { paddingTop: 12, paddingHorizontal: 16, paddingBottom: 4 },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 16, paddingVertical: 6 },
  infoValue: { flexShrink: 1, textAlign: 'right' },
  divider: { height: 1 },
  pressed: { opacity: 0.6 },
});
