import { Pressable, StyleSheet, View } from 'react-native';

import { tap } from '@/lib/haptics';
import { useTheme, withAlpha } from '@/theme';
import { COLORS } from '@/theme/colors';
import { setThemePref, THEME_LABELS, useThemePref, type ThemePref } from '@/theme/preference';
import { Icon } from '@/ui/icons/Icon';
import { SheetHeader } from '@/ui/SheetHeader';
import { Text } from '@/ui/Text';

const ORDER: ThemePref[] = ['system', 'light', 'dark'];

// A tiny screen in that theme: a balance card and two rows
function MiniScreen({ dark }: { dark: boolean }) {
  const c = COLORS[dark ? 'dark' : 'light'];
  return (
    <View style={[styles.mini, { backgroundColor: c.bg }]}>
      <View style={[styles.miniCard, { backgroundColor: c.cardB }]} />
      <View style={[styles.miniRow, { backgroundColor: withAlpha(c.ink, 0.16) }]} />
      <View style={[styles.miniRow, styles.miniShort, { backgroundColor: withAlpha(c.ink, 0.1) }]} />
    </View>
  );
}

function Preview({ pref }: { pref: ThemePref }) {
  if (pref !== 'system') return <MiniScreen dark={pref === 'dark'} />;
  // half and half: it follows the phone
  return (
    <View style={styles.split}>
      <MiniScreen dark={false} />
      <View style={styles.darkHalf}>
        <View style={styles.darkInner}>
          <MiniScreen dark />
        </View>
      </View>
    </View>
  );
}

// Theme picker under Profile: what each choice looks like, applied right away
export default function ThemeSheet() {
  const { c } = useTheme();
  const current = useThemePref();

  return (
    <View style={styles.sheet}>
      <SheetHeader title="Тема" />
      <View style={styles.options}>
        {ORDER.map((pref) => {
          const selected = pref === current;
          return (
            <Pressable
              key={pref}
              accessibilityRole="radio"
              accessibilityState={{ checked: selected }}
              accessibilityLabel={THEME_LABELS[pref]}
              onPress={() => {
                if (selected) return;
                tap();
                setThemePref(pref);
              }}
              style={({ pressed }) => [styles.option, pressed && styles.pressed]}
            >
              <View
                style={[
                  styles.frame,
                  { borderColor: selected ? c.accent : withAlpha(c.shade, 0.12) },
                ]}
              >
                <Preview pref={pref} />
              </View>
              <Text variant="bodyStrong" tone={selected ? 'ink' : 'muted'} style={styles.label}>
                {THEME_LABELS[pref]}
              </Text>
              <View
                style={[
                  styles.radio,
                  selected
                    ? { backgroundColor: c.accent, borderColor: c.accent }
                    : { borderColor: withAlpha(c.shade, 0.2) },
                ]}
              >
                {selected ? <Icon name="check" size={12} color={c.cream} weight={3} /> : null}
              </View>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const PREVIEW_H = 128;

const styles = StyleSheet.create({
  // the sheet floats above the home indicator, so the bottom needs no inset
  sheet: { paddingTop: 22, paddingHorizontal: 20, paddingBottom: 20, gap: 22 },
  options: { flexDirection: 'row', gap: 12 },
  option: { flex: 1, alignItems: 'center', gap: 10 },
  pressed: { opacity: 0.7 },
  frame: { alignSelf: 'stretch', height: PREVIEW_H, borderRadius: 18, borderWidth: 2, padding: 3 },
  mini: { flex: 1, borderRadius: 13, padding: 8, gap: 6, overflow: 'hidden' },
  miniCard: { height: 34, borderRadius: 8, marginBottom: 4 },
  miniRow: { height: 8, borderRadius: 4 },
  miniShort: { width: '60%' },
  split: { flex: 1 },
  // the right half shows the same mini screen in dark
  darkHalf: { position: 'absolute', top: 0, bottom: 0, right: 0, width: '50%', overflow: 'hidden', borderTopRightRadius: 13, borderBottomRightRadius: 13 },
  darkInner: { position: 'absolute', top: 0, bottom: 0, right: 0, width: '200%' },
  label: { fontSize: 13.5 },
  radio: { width: 21, height: 21, borderRadius: 11, borderWidth: 1.6, alignItems: 'center', justifyContent: 'center' },
});
