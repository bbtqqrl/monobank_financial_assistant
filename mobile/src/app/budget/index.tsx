import { router, useLocalSearchParams, useNavigation, type NativeStackNavigationProp } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useBudgets, useDeleteBudget, useSaveBudget, type Budget } from '@/api/budgets';
import { toBrief, useCategories } from '@/api/categories';
import { ApiError } from '@/api/client';
import { categoryLook } from '@/lib/categories';
import { budgetCategory, QUICK_SLUGS } from '@/lib/draft';
import { failure, success, tap } from '@/lib/haptics';
import { formatMoney, parseAmount, UAH } from '@/lib/money';
import { useMask } from '@/lib/privacy';
import { BudgetPreview } from '@/ui/BudgetPreview';
import { Button } from '@/ui/Button';
import { QuickCategories } from '@/ui/QuickCategories';
import { SheetHeader } from '@/ui/SheetHeader';
import { Text } from '@/ui/Text';

const close = () => (router.canGoBack() ? router.back() : router.replace('/budgets'));

// limits are whole hryvnias, "3 000"; kopiyky in the field would only be noise
const toText = (minor: number) => String(Math.round(minor / 100));

// A monthly limit for one spending category: a new one, or the limit of an
// existing one changed or removed (?id=)
export default function BudgetSheet() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const budgets = useBudgets();
  const existing = id ? budgets.data?.find((b) => b.id === Number(id)) : undefined;

  if (id && !budgets.data) return <ActivityIndicator style={styles.loading} />;
  // a fresh form per budget, so its limit fills the field
  return <BudgetForm key={existing?.id ?? 'new'} existing={existing} budgets={budgets.data ?? []} />;
}

function BudgetForm({ existing, budgets }: { existing?: Budget; budgets: Budget[] }) {
  const insets = useSafeAreaInsets();
  const mask = useMask();
  const categories = useCategories();
  const save = useSaveBudget();
  const remove = useDeleteBudget();
  const picked = budgetCategory.useValue();
  const [text, setText] = useState(() => (existing ? toText(existing.amount) : ''));

  useEffect(() => () => budgetCategory.set(null), []);

  // the keyboard waits for the sheet to settle: raised mid-slide, iOS scrolls
  // the content to keep the field above it and the card slides under the header
  const navigation = useNavigation<NativeStackNavigationProp<Record<string, object | undefined>>>();
  const amountInput = useRef<TextInput>(null);
  useEffect(
    () =>
      navigation.addListener('transitionEnd', (e) => {
        if (!e.data.closing) amountInput.current?.focus();
      }),
    [navigation],
  );

  const category = existing?.category ?? picked;
  // a category can have one budget; picking one that has it offers that budget instead
  const taken = !existing && category ? budgets.find((b) => b.category.id === category.id) : undefined;
  const amount = parseAmount(text, UAH);
  const changed = !existing || amount !== existing.amount;
  const ready = !!category && amount !== null && !taken && changed;
  const money = (v: number) => mask(formatMoney(v, UAH, { cents: false }));

  // frequent spending ones that don't have a budget yet
  const budgeted = new Set(budgets.map((b) => b.category.id));
  const bySlug = new Map((categories.data ?? []).flatMap((p) => [p, ...p.children]).map((n) => [n.slug, toBrief(n)]));
  const frequent = QUICK_SLUGS.expense.flatMap((slug) => bySlug.get(slug) ?? []).filter((q) => !budgeted.has(q.id));
  const quick = picked && !frequent.some((q) => q.id === picked.id) ? [picked, ...frequent] : frequent;
  const openCategories = () => {
    tap();
    router.push('/budget/category');
  };

  const caption = taken
    ? `На «${taken.category.name}» вже є бюджет`
    : existing
      ? `Витрачено ${money(existing.current_amount)} з ${money(amount ?? existing.amount)}`
      : 'Ліміт на місяць';
  const submit = () => {
    if (!ready || !category || amount === null) return;
    save.mutate(
      { id: existing?.id, categoryId: category.id, amount },
      {
        onSuccess: () => {
          success();
          close();
        },
        onError: (error) => {
          failure();
          Alert.alert(
            'Не вдалося зберегти',
            error instanceof ApiError && error.status === 409
              ? 'На цю категорію вже є бюджет'
              : error instanceof ApiError && error.status === 400
                ? 'На цю категорію не можна поставити ліміт'
                : 'Перевір інтернет і спробуй ще раз',
          );
        },
      },
    );
  };

  const confirmDelete = () => {
    if (!existing) return;
    Alert.alert(`Видалити бюджет «${existing.category.name}»?`, 'Витрати лишаться, зникне лише ліміт', [
      { text: 'Скасувати', style: 'cancel' },
      {
        text: 'Видалити',
        style: 'destructive',
        onPress: () =>
          remove.mutate(existing.id, {
            // its own screen is gone too
            onSuccess: () => router.dismissTo('/budgets'),
            onError: () => Alert.alert('Не вдалося видалити', 'Перевір інтернет і спробуй ще раз'),
          }),
      },
    ]);
  };

  return (
    <>
      <View collapsable={false} style={styles.top}>
        <SheetHeader title={existing ? 'Бюджет' : 'Новий бюджет'} />
      </View>

      {/* everything fits above the keyboard, nothing to scroll */}
      <ScrollView
        scrollEnabled={false}
        contentContainerStyle={[styles.content, { paddingBottom: Math.max(insets.bottom, 16) + 8 }]}
        keyboardShouldPersistTaps="handled"
      >
        <BudgetPreview
          look={category ? categoryLook(category.slug, -1) : null}
          name={category?.name ?? null}
          onCategoryPress={existing ? undefined : openCategories}
          amountText={text}
          onAmountText={setText}
          caption={caption}
          inputRef={amountInput}
        />

        {existing ? null : (
          <View style={styles.section}>
            <Text variant="labelCaps" tone="ghost" style={styles.label}>
              Категорія
            </Text>
            <QuickCategories
              categories={quick}
              selectedId={category?.id ?? null}
              income={false}
              onPick={budgetCategory.set}
              onMore={openCategories}
            />
          </View>
        )}

        {taken ? (
          <Button kind="secondary" label="Відкрити його" onPress={() => router.setParams({ id: String(taken.id) })} />
        ) : (
          <Button
            label={existing ? 'Зберегти' : amount !== null && category ? `Додати ${money(amount)}` : 'Додати бюджет'}
            onPress={submit}
            disabled={!ready}
            loading={save.isPending}
          />
        )}

        {existing ? (
          <Pressable accessibilityRole="button" onPress={confirmDelete} style={({ pressed }) => [styles.delete, pressed && styles.pressed]}>
            <Text variant="bodyStrong" tone="danger">
              Видалити бюджет
            </Text>
          </Pressable>
        ) : null}
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  loading: { marginTop: 40 },
  top: { paddingTop: 22, paddingHorizontal: 20, paddingBottom: 6 },
  content: { paddingHorizontal: 20, paddingTop: 8, gap: 20 },
  section: { gap: 10 },
  label: { paddingHorizontal: 4 },
  pressed: { opacity: 0.6 },
  delete: { alignItems: 'center', paddingVertical: 4 },
});
