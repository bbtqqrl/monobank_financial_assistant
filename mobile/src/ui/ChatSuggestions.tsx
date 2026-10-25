import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';

import { Fragment } from 'react';

import { FONT } from '@/lib/fonts';
import { tap } from '@/lib/haptics';
import { useTheme, whiteAlpha, withAlpha } from '@/theme';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

// a short label on the chip, the whole question when sent
export type Suggestion = { label: string; prompt: string };

// questions the assistant has the data for, to show what it can do
const STARTERS: (Suggestion & { icon: IconName })[] = [
  { icon: 'calendar', label: 'Витрати за місяць', prompt: 'Скільки я витратив цього місяця?' },
  { icon: 'chart', label: 'Куди йдуть гроші', prompt: 'На що йде найбільше грошей?' },
  { icon: 'repeat', label: 'Регулярні платежі', prompt: 'Які в мене регулярні платежі?' },
  { icon: 'jar', label: 'Де заощадити', prompt: 'Де я можу заощадити?' },
];

// what to ask next, by the tools behind the last answer
const FOLLOW_UPS: Record<string, Suggestion[]> = {
  get_spending: [
    { label: 'По категоріях', prompt: 'Розклади ці витрати по категоріях' },
    { label: 'Порівняй з минулим місяцем', prompt: 'Порівняй з минулим місяцем' },
  ],
  get_categories_breakdown: [
    { label: 'Де найбільше?', prompt: 'Де саме я витрачаю найбільше?' },
    { label: 'Як змінювалось?', prompt: 'Як ці категорії змінювались за останні місяці?' },
  ],
  get_merchants: [{ label: 'Як часто туди ходжу?', prompt: 'Як часто я там витрачаю і скільки за раз?' }],
  get_recurring: [{ label: 'Що можна скасувати?', prompt: 'Які з цих платежів можна скасувати?' }],
  get_budgets: [{ label: 'Де перевищую?', prompt: 'У яких бюджетах я перевищую ліміт?' }],
  search_transactions: [{ label: 'Скільки разом?', prompt: 'Скільки це разом?' }],
};

const MAX_FOLLOW_UPS = 3;

// asked: the question just answered, not offered again
export function followUpsFor(tools: string[], asked?: string): Suggestion[] {
  const seen = new Set<string>(asked ? [asked] : []);
  const picked = tools.flatMap((t) => FOLLOW_UPS[t] ?? []).filter((s) => !seen.has(s.prompt) && seen.add(s.prompt));
  const fallback = STARTERS.filter((s) => s.prompt !== asked).slice(0, 2);
  return (picked.length ? picked : fallback).slice(0, MAX_FOLLOW_UPS);
}

function Chip({ item, onPick }: { item: Suggestion; onPick: (prompt: string) => void }) {
  const { c, dark } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={item.prompt}
      onPress={() => {
        tap();
        onPick(item.prompt);
      }}
      style={({ pressed }) => [
        styles.chip,
        // a lighter cousin of the glass cards: the same white veil and rim, no shadow
        {
          backgroundColor: withAlpha(c.white, whiteAlpha(0.5, dark)),
          borderColor: withAlpha(c.white, whiteAlpha(0.8, dark)),
        },
        pressed && styles.pressed,
      ]}
    >
      <Text variant="labelSection" numberOfLines={1}>
        {item.label}
      </Text>
    </Pressable>
  );
}

// a row of chips after an answer, scrolling sideways when they don't fit
export function FollowUps({ items, onPick }: { items: Suggestion[]; onPick: (prompt: string) => void }) {
  return (
    <Animated.View entering={FadeIn.duration(220)}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
        keyboardShouldPersistTaps="handled"
      >
        {items.map((s) => (
          <Chip key={s.label} item={s} onPick={onPick} />
        ))}
      </ScrollView>
    </Animated.View>
  );
}

// One starter question as a plain line: its icon and the question itself
function Starter({ item, onPick }: { item: (typeof STARTERS)[number]; onPick: (prompt: string) => void }) {
  const { c } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => {
        tap();
        onPick(item.prompt);
      }}
      style={({ pressed }) => [styles.starter, pressed && styles.pressed]}
    >
      <Icon name={item.icon} size={18} color={c.onBackdrop} />
      <Text style={styles.starterText} numberOfLines={1}>
        {item.prompt}
      </Text>
    </Pressable>
  );
}

// A new chat: a line about what it can do and a few questions to start with,
// tucked away once something is typed
export function ChatSuggestions({ onPick, chips = true }: { onPick: (prompt: string) => void; chips?: boolean }) {
  const { c } = useTheme();
  return (
    <View style={styles.column}>
      <View style={styles.intro}>
        <Text variant="screenTitle" style={styles.title}>
          Питай про свої гроші
        </Text>
        <Text variant="body" tone="onBackdrop" style={styles.caption}>
          Бачу твої картки, банки й бюджети, тож відповідаю твоїми цифрами
        </Text>
      </View>
      {chips ? (
        <Animated.View entering={FadeIn.duration(160)} exiting={FadeOut.duration(160)}>
          {STARTERS.map((s, i) => (
            <Fragment key={s.label}>
              {i > 0 ? <View style={[styles.divider, { backgroundColor: withAlpha(c.ink, 0.08) }]} /> : null}
              <Starter item={s} onPick={onPick} />
            </Fragment>
          ))}
        </Animated.View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  column: { gap: 10 },
  intro: { gap: 4 },
  title: { fontSize: 22, lineHeight: 28 },
  caption: { fontSize: 14, lineHeight: 19 },
  starter: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12 },
  starterText: { flex: 1, fontFamily: FONT.ui.medium, fontSize: 15, lineHeight: 20 },
  divider: { height: StyleSheet.hairlineWidth, marginLeft: 30 },
  row: { gap: 8, paddingHorizontal: 20 },
  chip: {
    height: 36,
    borderRadius: 18,
    borderCurve: 'continuous',
    paddingHorizontal: 14,
    borderWidth: 1,
    justifyContent: 'center',
  },
  pressed: { opacity: 0.6 },
});
