import { router, useLocalSearchParams, useNavigation, type NativeStackNavigationProp } from 'expo-router';
import { useEffect, useRef, useState, type RefObject } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useBudgets, useDeleteBudget, useSaveBudget, type Budget } from '@/api/budgets';
import { toBrief, useCategories } from '@/api/categories';
import { ApiError } from '@/api/client';
import { categoryLook } from '@/lib/categories';
import { budgetCategory, QUICK_SLUGS } from '@/lib/draft';
import { FONT } from '@/lib/fonts';
import { failure, success, tap, thud, warning } from '@/lib/haptics';
import { formatMoney, parseAmount, UAH } from '@/lib/money';
import { useMask } from '@/lib/privacy';
import { useTheme, withAlpha } from '@/theme';
import { BudgetPreview } from '@/ui/BudgetPreview';
import { limitTone } from '@/ui/BudgetRow';
import { Button } from '@/ui/Button';
import { CategoryChip } from '@/ui/CategoryChip';
import { Icon } from '@/ui/icons/Icon';
import { LimitField } from '@/ui/LimitField';
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
  // a fresh editor per budget, so its limit fills the field
  if (existing) return <LimitEditor key={existing.id} budget={existing} />;
  return <BudgetForm budgets={budgets.data ?? []} />;
}

// The keyboard waits for the sheet to settle: raised mid-slide, iOS scrolls
// the content to keep the field above it and the card slides under the header
function useFocusWhenOpen(input: RefObject<TextInput | null>) {
  const navigation = useNavigation<NativeStackNavigationProp<Record<string, object | undefined>>>();
  useEffect(
    () =>
      navigation.addListener('transitionEnd', (e) => {
        if (!e.data.closing) input.current?.focus();
      }),
    [navigation, input],
  );
}

function saveError(error: unknown) {
  failure();
  Alert.alert(
    'Не вдалося зберегти',
    error instanceof ApiError && error.status === 409
      ? 'На цю категорію вже є бюджет'
      : error instanceof ApiError && error.status === 400
        ? 'На цю категорію не можна поставити ліміт'
        : 'Перевір інтернет і спробуй ще раз',
  );
}

function BudgetForm({ budgets }: { budgets: Budget[] }) {
  const insets = useSafeAreaInsets();
  const mask = useMask();
  const categories = useCategories();
  const save = useSaveBudget();
  const category = budgetCategory.useValue();
  const [text, setText] = useState('');

  useEffect(() => () => budgetCategory.set(null), []);

  const amountInput = useRef<TextInput>(null);
  useFocusWhenOpen(amountInput);

  // a category can have one budget; picking one that has it offers that budget instead
  const taken = category ? budgets.find((b) => b.category.id === category.id) : undefined;
  const amount = parseAmount(text, UAH);
  const ready = !!category && amount !== null && !taken;
  const money = (v: number) => mask(formatMoney(v, UAH, { cents: false }));

  // frequent spending ones that don't have a budget yet
  const budgeted = new Set(budgets.map((b) => b.category.id));
  const bySlug = new Map((categories.data ?? []).flatMap((p) => [p, ...p.children]).map((n) => [n.slug, toBrief(n)]));
  const frequent = QUICK_SLUGS.expense.flatMap((slug) => bySlug.get(slug) ?? []).filter((q) => !budgeted.has(q.id));
  const quick = category && !frequent.some((q) => q.id === category.id) ? [category, ...frequent] : frequent;
  const openCategories = () => {
    tap();
    router.push('/budget/category');
  };

  const caption = taken ? `На «${taken.category.name}» вже є бюджет` : 'Ліміт на місяць';
  const submit = () => {
    if (!ready || !category || amount === null) return;
    save.mutate(
      { categoryId: category.id, amount },
      {
        onSuccess: () => {
          success();
          close();
        },
        onError: saveError,
      },
    );
  };

  return (
    <>
      <View collapsable={false} style={styles.top}>
        <SheetHeader title="Новий бюджет" />
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
          onCategoryPress={openCategories}
          amountText={text}
          onAmountText={setText}
          caption={caption}
          inputRef={amountInput}
        />

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

        {taken ? (
          <Button kind="secondary" label="Відкрити його" onPress={() => router.setParams({ id: String(taken.id) })} />
        ) : (
          <Button
            label={amount !== null && category ? `Додати ${money(amount)}` : 'Додати бюджет'}
            onPress={submit}
            disabled={!ready}
            loading={save.isPending}
          />
        )}
      </ScrollView>
    </>
  );
}

// Changing a budget's limit, mostly reached by holding its row: just the
// number, how the month's spending sits against it, and the way to remove it
function LimitEditor({ budget }: { budget: Budget }) {
  const { c, dark } = useTheme();
  const mask = useMask();
  const save = useSaveBudget();
  const remove = useDeleteBudget();
  const [text, setText] = useState(() => toText(budget.amount));
  const input = useRef<TextInput>(null);
  useFocusWhenOpen(input);

  const look = categoryLook(budget.category.slug, -1);
  const amount = parseAmount(text, UAH);
  const ready = amount !== null && amount !== budget.amount;
  const spent = budget.current_amount;
  // what the bar and the line under it show for the limit being typed
  const limit = amount ?? budget.amount;
  const ratio = limit > 0 ? spent / limit : 0;
  const left = limit - spent;
  const money = (v: number) => mask(formatMoney(v, UAH, { cents: false }));

  const fill = useSharedValue(Math.min(ratio, 1));
  useEffect(() => {
    fill.set(withTiming(Math.min(ratio, 1), { duration: 260 }));
  }, [ratio, fill]);
  const fillStyle = useAnimatedStyle(() => ({ width: `${fill.get() * 100}%` }));

  const submit = () => {
    if (!ready || amount === null) return;
    save.mutate(
      { id: budget.id, categoryId: budget.category.id, amount },
      {
        onSuccess: () => {
          success();
          close();
        },
        onError: saveError,
      },
    );
  };

  const confirmDelete = () => {
    warning();
    Alert.alert(`Видалити бюджет «${budget.category.name}»?`, 'Витрати лишаться, зникне лише ліміт', [
      { text: 'Скасувати', style: 'cancel' },
      {
        text: 'Видалити',
        style: 'destructive',
        onPress: () =>
          remove.mutate(budget.id, {
            onSuccess: () => {
              thud();
              // its own screen is gone too
              router.dismissTo('/budgets');
            },
            onError: () => {
              failure();
              Alert.alert('Не вдалося видалити', 'Перевір інтернет і спробуй ще раз');
            },
          }),
      },
    ]);
  };

  return (
    <View style={styles.editor}>
      <View style={styles.editorHead}>
        <CategoryChip {...look} size={40} radius={13} />
        <View style={styles.editorTitle}>
          <Text variant="bodyStrong" numberOfLines={1} style={styles.editorName}>
            {budget.category.name}
          </Text>
          <Text variant="rowCaption" tone="faint">
            Ліміт на місяць
          </Text>
        </View>
      </View>

      <View style={styles.editorAmount}>
        <LimitField text={text} onText={setText} inputRef={input} />
      </View>

      <View style={styles.meter}>
        <View style={[styles.track, { backgroundColor: withAlpha(c.shade, dark ? 0.12 : 0.08) }]}>
          <Animated.View
            style={[styles.fill, { backgroundColor: limitTone(ratio, c.category[look.color], c) }, fillStyle]}
          />
        </View>
        <View style={styles.meterLine}>
          <Text variant="rowCaption" tone="muted">
            Витрачено {money(spent)}
          </Text>
          {left >= 0 ? (
            <Text variant="rowCaption" tone="faint">
              Лишиться {money(left)}
            </Text>
          ) : (
            <Text variant="rowCaption" tone="danger" style={styles.over}>
              Понад ліміт на {money(-left)}
            </Text>
          )}
        </View>
      </View>

      <View style={styles.editorActions}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Видалити бюджет"
          onPress={confirmDelete}
          style={({ pressed }) => [
            styles.trash,
            { backgroundColor: withAlpha(c.danger, 0.12), borderColor: withAlpha(c.danger, 0.22) },
            pressed && styles.pressed,
          ]}
        >
          <Icon name="trash" size={20} color={c.danger} weight={1.9} />
        </Pressable>
        <View style={styles.grow}>
          <Button label="Зберегти" onPress={submit} disabled={!ready} loading={save.isPending} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  loading: { marginTop: 40 },
  top: { paddingTop: 22, paddingHorizontal: 20, paddingBottom: 6 },
  content: { paddingHorizontal: 20, paddingTop: 8, gap: 20 },
  section: { gap: 10 },
  label: { paddingHorizontal: 4 },
  pressed: { opacity: 0.6 },
  editor: { paddingTop: 26, paddingHorizontal: 20, paddingBottom: 20, gap: 22 },
  editorHead: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  editorTitle: { flex: 1, gap: 2 },
  editorName: { fontSize: 16, lineHeight: 21 },
  editorAmount: { alignItems: 'center' },
  meter: { gap: 8 },
  track: { height: 8, borderRadius: 4, overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4 },
  meterLine: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
  over: { fontFamily: FONT.ui.semiBold },
  editorActions: { flexDirection: 'row', gap: 10 },
  trash: { width: 54, height: 54, borderRadius: 19, borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  grow: { flex: 1 },
});
