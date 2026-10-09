import { router, useLocalSearchParams } from 'expo-router';
import { Fragment } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

import { accountLabel, useAccountCurrencies, useAccounts } from '@/api/accounts';
import { ApiError } from '@/api/client';
import { foreignPart, txCurrency, useTransaction, type TransactionDetail } from '@/api/transactions';
import { categoryLook } from '@/lib/categories';
import { formatMoney } from '@/lib/money';
import { fullDate } from '@/lib/time';
import { goBack } from '@/lib/nav';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { Button } from '@/ui/Button';
import { CategoryChip } from '@/ui/CategoryChip';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Screen } from '@/ui/Screen';
import { Text } from '@/ui/Text';

// where the category came from, see category_source in the backend
function sourceLine(t: TransactionDetail): { icon: IconName; text: string } {
  const pct = t.category_confidence !== null ? ` · ${Math.round(t.category_confidence * 100)}%` : '';
  switch (t.category_source) {
    case 'user':
      return { icon: 'pencil', text: 'Обрано вручну' };
    case 'rule':
      return { icon: 'list', text: 'За кодом MCC' };
    case 'mapping':
      return { icon: 'repeat', text: `Як раніше для «${t.description}»` };
    case 'ai':
      return { icon: 'sparkle', text: `Визначено автоматично${pct}` };
    case 'mapping_low_confidence':
    case 'ai_low_confidence':
      return { icon: 'sparkle', text: `Невпевнено${pct} · перевір` };
    case 'ai_failed':
      return { icon: 'close', text: 'Не вдалося визначити' };
    default:
      return { icon: 'sparkle', text: 'Ще визначаємо' };
  }
}

export default function TransactionScreen() {
  const { c } = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const tx = useTransaction(Number(id));
  const accounts = useAccounts();
  const currencies = useAccountCurrencies();
  const t = tx.data;

  const header = (
    <Header
      title="Деталі транзакції"
      small
      left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
      right={{ icon: 'dots', label: 'Ще', weight: 2.4 }}
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
  const changeCategory = () => router.push({ pathname: '/transaction/[id]/category', params: { id: String(t.id) } });

  const info: [string, string][] = [];
  if (account) info.push(['Рахунок', accountLabel(account)]);
  else if (t.jar_id !== null) info.push(['Рахунок', 'Банка']);
  if (original) info.push(['Сума покупки', formatMoney(original.amount, original.currency, { sign: 'never' })]);
  if (t.counter_name) info.push(['Отримувач', t.counter_name]);
  if (t.comment) info.push(['Коментар', t.comment]);
  if (t.mcc !== null) info.push(['MCC', String(t.mcc)]);
  // like the card balance, without the credit limit
  if (t.balance !== null) info.push(['Баланс після', formatMoney(t.balance - (account?.credit_limit ?? 0), currency)]);

  return (
    <Screen background="green">
      {header}

      <View style={styles.hero}>
        <CategoryChip {...look} size={62} radius={22} />
        <Text variant="bodyStrong" style={styles.title} numberOfLines={2}>
          {t.description}
        </Text>
        <Text style={[TEXT.amountXl, styles.amount, { color: income ? c.category.green : c.ink }]}>
          {formatMoney(t.amount, currency, { sign: income ? 'always' : 'auto' })}
        </Text>
        <Text variant="rowCaption" tone="faint" style={styles.date}>
          {fullDate(t.time)}
        </Text>
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityHint="Змінити категорію"
        onPress={changeCategory}
        style={({ pressed }) => pressed && styles.pressed}
      >
        <Glass radius={22} contentStyle={styles.category}>
          <Text variant="labelCaps" tone="ghost">
            Категорія
          </Text>
          <View style={styles.categoryRow}>
            <CategoryChip {...look} size={36} radius={12} />
            <View style={styles.categoryText}>
              <Text variant="bodyStrong" style={styles.categoryName}>
                {t.category?.name ?? 'Без категорії'}
              </Text>
              <View style={styles.source}>
                <Icon name={src.icon} size={11} color={c.accent} weight={2.2} />
                <Text variant="rowCaption" tone="muted" style={styles.sourceText}>
                  {src.text}
                </Text>
              </View>
            </View>
            <Icon name="chevronRight" size={18} color={c.ghost} weight={1.9} />
          </View>
        </Glass>
      </Pressable>

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

      <Button label="Змінити категорію" onPress={changeCategory} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  message: { paddingVertical: 40, textAlign: 'center' },
  hero: { alignItems: 'center', gap: 7, paddingTop: 2, paddingBottom: 4 },
  title: { fontSize: 16, lineHeight: 21, textAlign: 'center' },
  amount: { fontSize: 29, lineHeight: 33, letterSpacing: -0.29, fontVariant: ['tabular-nums'] },
  date: { fontSize: 12.5 },
  // Figma: 12 16 12 16
  category: { paddingVertical: 12, paddingHorizontal: 16, gap: 9 },
  categoryRow: { flexDirection: 'row', alignItems: 'center', gap: 11 },
  categoryText: { flex: 1, gap: 4 },
  categoryName: { fontSize: 14.5, lineHeight: 19 },
  source: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  sourceText: { fontSize: 11.5 },
  // Figma: 12 16 4 16
  info: { paddingTop: 12, paddingHorizontal: 16, paddingBottom: 4 },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 16, paddingVertical: 6 },
  infoValue: { flexShrink: 1, textAlign: 'right' },
  divider: { height: 1 },
  pressed: { opacity: 0.6 },
});
