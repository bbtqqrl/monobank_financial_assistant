import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn, LayoutAnimationConfig } from 'react-native-reanimated';

import { createStore, type Store } from '@/lib/store';
import type { RefreshStatus } from '@/lib/usePullRefresh';
import { useTheme } from '@/theme';
import { IconButton, type IconButtonProps } from '@/ui/IconButton';
import { Icon } from '@/ui/icons/Icon';
import { SpinIcon } from '@/ui/SpinIcon';
import { Text } from '@/ui/Text';

type Props = {
  title: string;
  left?: IconButtonProps;
  right?: IconButtonProps;
  // detail screens use a smaller title
  small?: boolean;
  // a pull-to-refresh, shown in place of the title while it runs and for a
  // moment after; read here so the screen doesn't re-render for it
  status?: Store<RefreshStatus>;
};

const IDLE = createStore<RefreshStatus>(null);

const FADE = FadeIn.duration(180);

// Screen header: glass button · title · glass button. A missing button keeps
// its slot so the title stays centred.
export function Header({ title, left, right, small = false, status = IDLE }: Props) {
  const { c } = useTheme();
  const note = status.useValue();

  return (
    <View style={styles.row}>
      {left ? <IconButton {...left} /> : <View style={styles.slot} />}
      <View style={styles.middle}>
        {/* the title shows up as is when the screen opens, it only fades back after a note */}
        <LayoutAnimationConfig skipEntering>
          {note === 'busy' ? (
            <Animated.View key="busy" entering={FADE} style={styles.note}>
              <SpinIcon spinning color={c.muted} size={15} />
              <Text variant="bodyStrong" numberOfLines={1} style={[styles.noteText, { color: c.muted }]}>
                Оновлення…
              </Text>
            </Animated.View>
          ) : note ? (
            <Animated.View key={note.text} entering={FADE} style={styles.note}>
              <Icon name={note.ok ? 'check' : 'close'} size={15} color={note.ok ? c.category.green : c.danger} weight={2.4} />
              <Text variant="bodyStrong" numberOfLines={1} style={[styles.noteText, { color: note.ok ? c.ink : c.danger }]}>
                {note.text}
              </Text>
            </Animated.View>
          ) : (
            <Animated.View key="title" entering={FADE} style={styles.titleBox}>
              <Text
                variant="screenTitle"
                numberOfLines={1}
                accessibilityRole="header"
                style={[styles.title, small && styles.small]}
              >
                {title}
              </Text>
            </Animated.View>
          )}
        </LayoutAnimationConfig>
      </View>
      {right ? <IconButton {...right} /> : <View style={styles.slot} />}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  slot: { width: 44, height: 44 },
  middle: { flex: 1, alignItems: 'center' },
  titleBox: { alignSelf: 'stretch' },
  title: { textAlign: 'center' },
  small: { fontSize: 15, lineHeight: 19, letterSpacing: -0.15 },
  note: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  noteText: { fontSize: 14.5, flexShrink: 1 },
});
