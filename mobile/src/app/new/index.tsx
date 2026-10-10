import { router } from 'expo-router';
import { useEffect, useState, type ReactNode } from 'react';
import { Alert, ScrollView, StyleSheet, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { accountName, sortedAccounts, useAccounts } from '@/api/accounts';
import { toBrief, useCategories } from '@/api/categories';
import { ApiError } from '@/api/client';
import { useCreateTransaction } from '@/api/transactions';
import { categoryLook } from '@/lib/categories';
import { cardOrder, hiddenCards } from '@/lib/cardOrder';
import { DRAFT_KINDS, QUICK_SLUGS, draftCategory, type DraftDirection } from '@/lib/draft';
import { failure, success, tap } from '@/lib/haptics';
import { formatMoney, parseAmount, UAH } from '@/lib/money';
import { isoDate, parseIso } from '@/lib/period';
import { dayLabel } from '@/lib/time';
import { AccountTiles } from '@/ui/AccountTiles';
import { Button } from '@/ui/Button';
import { DraftPreview } from '@/ui/DraftPreview';
import { Glass } from '@/ui/Glass';
import { Pill, PillRow } from '@/ui/Pill';
import { QuickCategories } from '@/ui/QuickCategories';
import { RangeCalendar } from '@/ui/RangeCalendar';
import { SheetHeader } from '@/ui/SheetHeader';
import { Text } from '@/ui/Text';

const daysBack = (n: number, now = new Date()) =>
  isoDate(new Date(now.getFullYear(), now.getMonth(), now.getDate() - n));

// the picked day at the current time of day, so today's entry is "now"
function timeOn(day: string, now = new Date()) {
  const d = parseIso(day);
  const at = new Date(d.getFullYear(), d.getMonth(), d.getDate(), now.getHours(), now.getMinutes(), now.getSeconds());
  return Math.floor(Math.min(at.getTime(), now.getTime()) / 1000);
}

const close = () => (router.canGoBack() ? router.back() : router.replace('/'));

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <View style={styles.section}>
      <Text variant="labelCaps" tone="ghost" style={styles.label}>
        {title}
      </Text>
      {children}
    </View>
  );
}

// New transaction sheet, opened by «+» in the tab bar: money the bank
export default function NewTransactionSheet() {
  const insets = useSafeAreaInsets();
  const accounts = useAccounts();
  const categories = useCategories();
  const create = useCreateTransaction();
  const category = draftCategory.useValue();
  const order = cardOrder.useValue();
  const hidden = hiddenCards.useValue();
  const [direction, setDirection] = useState<DraftDirection>('expense');
  const [amountText, setAmountText] = useState('');
  const [description, setDescription] = useState('');
  // null is cash
  const [accountId, setAccountId] = useState<number | null>(null);
  const [day, setDay] = useState(() => daysBack(0));
  const [calendarOpen, setCalendarOpen] = useState(false);

  useEffect(() => () => draftCategory.set(null), []);

  const income = direction === 'income';
  const account = accounts.data?.find((a) => a.id === accountId);
  const currency = account?.currency_code ?? UAH;
  const minor = parseAmount(amountText, currency);
  const signed = minor === null ? null : income ? minor : -minor;
  const today = daysBack(0);
  const yesterday = daysBack(1);
  const otherDay = day !== today && day !== yesterday;

  const bySlug = new Map((categories.data ?? []).flatMap((p) => [p, ...p.children]).map((n) => [n.slug, toBrief(n)]));
  const frequent = QUICK_SLUGS[direction].flatMap((slug) => bySlug.get(slug) ?? []);
  const quick = category && !frequent.some((q) => q.id === category.id) ? [category, ...frequent] : frequent;

  const openCategories = () => router.push({ pathname: '/new/category', params: { direction } });

  const pickDay = (next: string) => {
    if (next === day) return;
    tap();
    setDay(next);
  };

  const changeDirection = (next: DraftDirection) => {
    setDirection(next);
    if (category && !DRAFT_KINDS[next].includes(category.kind)) draftCategory.set(null);
  };

  const save = () => {
    if (signed === null || !category) return;
    create.mutate(
      {
        description: description.trim() || category.name,
        amount: signed,
        currency_code: currency,
        category_id: category.id,
        account_id: accountId,
        time: timeOn(day),
      },
      {
        onSuccess: () => {
          success();
          close();
        },
        onError: (error) => {
          failure();
          Alert.alert(
            'Не вдалося зберегти',
            error instanceof ApiError && error.status === 400
              ? 'Ця категорія не підходить для такої суми'
              : 'Перевір інтернет і спробуй ще раз',
          );
        },
      },
    );
  };

  return (
    <>
      <View collapsable={false} style={styles.top}>
        <SheetHeader title="Нова транзакція" />
      </View>

      <ScrollView
        contentContainerStyle={[styles.content, { paddingBottom: Math.max(insets.bottom, 16) + 8 }]}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        automaticallyAdjustKeyboardInsets
      >
        <DraftPreview
          direction={direction}
          onDirection={changeDirection}
          look={category ? categoryLook(category.slug, income ? 1 : -1) : null}
          onCategoryPress={openCategories}
          amountText={amountText}
          onAmountText={setAmountText}
          currency={currency}
          description={description}
          onDescription={setDescription}
          // left empty, the category name is used
          descriptionHint={category?.name ?? 'Опис'}
          summary={[category?.name ?? 'Без категорії', account ? accountName(account) : 'Готівка', dayLabel(timeOn(day))].join(
            ' · ',
          )}
        />

        <Section title="Категорія">
          <QuickCategories
            categories={quick}
            selectedId={category?.id ?? null}
            income={income}
            onPick={draftCategory.set}
            onMore={openCategories}
          />
        </Section>

        <Section title="Рахунок">
          <AccountTiles
            accounts={sortedAccounts(accounts.data ?? [], order).filter((a) => !hidden.includes(a.id))}
            value={accountId}
            onChange={setAccountId}
          />
        </Section>

        <Section title="Дата">
          <PillRow wrap>
            <Pill label="Сьогодні" active={day === today} onPress={() => pickDay(today)} />
            <Pill label="Вчора" active={day === yesterday} onPress={() => pickDay(yesterday)} />
            <Pill
              label={otherDay ? dayLabel(timeOn(day)) : 'Інший день'}
              icon="calendar"
              active={otherDay || calendarOpen}
              onPress={() => {
                tap();
                setCalendarOpen((open) => !open);
              }}
            />
          </PillRow>
          {calendarOpen ? (
            <Animated.View entering={FadeIn.duration(180)}>
              <Glass radius={20} contentStyle={styles.calendar}>
                <RangeCalendar
                  single
                  from={day}
                  onChange={(picked) => {
                    if (picked) pickDay(picked);
                    setCalendarOpen(false);
                  }}
                />
              </Glass>
            </Animated.View>
          ) : null}
        </Section>

        <Button
          label={signed !== null && category ? `Додати ${formatMoney(signed, currency)}` : 'Додати'}
          onPress={save}
          disabled={signed === null || !category}
          loading={create.isPending}
        />
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  top: { paddingTop: 22, paddingHorizontal: 20, paddingBottom: 6 },
  content: { paddingHorizontal: 20, paddingTop: 8, gap: 20 },
  section: { gap: 10 },
  label: { paddingHorizontal: 4 },
  calendar: { padding: 12 },
});
