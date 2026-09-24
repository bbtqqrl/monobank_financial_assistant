import { ScrollView, StyleSheet, Text, View, useColorScheme } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { FONT } from '@/lib/fonts';

// dev screen: checks Hermes Intl for uk/pl/en + fonts

type Check = { name: string; expected: string; actual: string };

// ICU uses narrow/no-break spaces
const NBSP = /[  ]/g;

function run(name: string, expected: string, fn: () => string): Check {
  let actual: string;
  try {
    actual = fn();
  } catch (e) {
    actual = `✗ ${e instanceof Error ? e.message : String(e)}`;
  }
  return { name, expected, actual };
}

function checks(): Check[] {
  const d = new Date(2026, 4, 20, 10, 32);
  return [
    run('NumberFormat uk-UA', '1 234 567,89', () => new Intl.NumberFormat('uk-UA').format(1234567.89)),
    run('NumberFormat pl-PL', '1 234 567,89', () => new Intl.NumberFormat('pl-PL').format(1234567.89)),
    run('NumberFormat en-GB', '1,234,567.89', () => new Intl.NumberFormat('en-GB').format(1234567.89)),
    run('PluralRules uk 1/2/5/21', 'one/few/many/one', () => {
      const p = new Intl.PluralRules('uk');
      return [1, 2, 5, 21].map((n) => p.select(n)).join('/');
    }),
    run('PluralRules pl 1/2/7/22/12', 'one/few/many/few/many', () => {
      const p = new Intl.PluralRules('pl');
      return [1, 2, 7, 22, 12].map((n) => p.select(n)).join('/');
    }),
    run('DateTimeFormat uk day+month', '20 травня', () =>
      new Intl.DateTimeFormat('uk', { day: 'numeric', month: 'long' }).format(d)),
    run('DateTimeFormat pl day+month', '20 maja', () =>
      new Intl.DateTimeFormat('pl', { day: 'numeric', month: 'long' }).format(d)),
    run('DateTimeFormat uk time', '10:32', () =>
      new Intl.DateTimeFormat('uk', { hour: '2-digit', minute: '2-digit' }).format(d)),
    run('DateTimeFormat uk month', 'травень', () =>
      new Intl.DateTimeFormat('uk', { month: 'long' }).format(d)),
    run('RelativeTimeFormat uk', '2 хвилини тому', () =>
      new Intl.RelativeTimeFormat('uk').format(-2, 'minute')),
    run('toLocaleUpperCase uk', 'ПРОДУКТИ ТА СУПЕРМАРКЕТИ', () =>
      'продукти та супермаркети'.toLocaleUpperCase('uk')),
    run('Collator uk', 'Аптека,Бюджет,Ґудзик,Епіцентр,Їжа', () =>
      ['Їжа', 'Епіцентр', 'Ґудзик', 'Аптека', 'Бюджет'].sort(new Intl.Collator('uk').compare).join(',')),
  ];
}

export default function SmokeScreen() {
  const dark = useColorScheme() === 'dark';
  const ink = dark ? '#F0EDE6' : '#1A1714';
  const results = checks();
  const failed = results.filter((c) => c.actual.replace(NBSP, ' ') !== c.expected);
  const engine = (globalThis as { HermesInternal?: unknown }).HermesInternal ? 'Hermes' : 'JSC';

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: dark ? '#141318' : '#EFEDE8' }]} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.body}>
        <Text style={[styles.title, { color: ink }]}>Intl check</Text>
        <Text style={[styles.summary, { color: failed.length ? '#C25A4E' : '#1F8A5F' }]}>
          {failed.length ? `${failed.length} of ${results.length} failed` : `All ${results.length} passed`} · {engine}
        </Text>
        {results.map((c) => {
          const ok = c.actual.replace(NBSP, ' ') === c.expected;
          return (
            <View key={c.name} style={[styles.row, { borderColor: ok ? '#1F8A5F55' : '#C25A4E88' }]}>
              <Text style={[styles.name, { color: ink }]}>{ok ? '✓' : '✗'} {c.name}</Text>
              <Text style={[styles.mono, { color: ink }]}>{c.actual}</Text>
              {!ok ? <Text style={[styles.mono, { color: '#8C857C' }]}>expected: {c.expected}</Text> : null}
            </View>
          );
        })}
        <Text style={[styles.fontLine, { color: ink, fontFamily: FONT.display.medium }]}>Rubik Medium — 72 540,18 ₴</Text>
        <Text style={[styles.fontLine, { color: ink, fontFamily: FONT.ui.bold }]}>Manrope Bold — 72 540,18 ₴</Text>
        <Text style={[styles.fontLine, { color: ink, fontFamily: FONT.ui.regular }]}>Manrope Regular — ґ є і ї ą ę ł ś ż</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  body: { padding: 20, gap: 10 },
  title: { fontFamily: FONT.display.medium, fontSize: 24, letterSpacing: -0.24 },
  summary: { fontFamily: FONT.ui.semiBold, fontSize: 14, marginBottom: 6 },
  row: { borderWidth: 1, borderRadius: 12, padding: 10, gap: 3 },
  name: { fontFamily: FONT.ui.semiBold, fontSize: 13 },
  mono: { fontFamily: FONT.ui.medium, fontSize: 13, fontVariant: ['tabular-nums'] },
  fontLine: { fontSize: 20, marginTop: 8 },
});
