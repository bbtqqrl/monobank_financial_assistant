import { useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
// gesture-handler's own, so a swipe cancels the press instead of opening the chat
import { Pressable } from 'react-native-gesture-handler';
import ReanimatedSwipeable from 'react-native-gesture-handler/ReanimatedSwipeable';
import Animated, { interpolate, useAnimatedStyle, type SharedValue } from 'react-native-reanimated';

import { FONT } from '@/lib/fonts';
import { hold, tap, thud } from '@/lib/haptics';
import { useTheme } from '@/theme';
import { Icon } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

const ACTION_W = 84;
const TITLE_MAX = 60;
// the pill keeps off the screen edge and off the row it comes out of
const EDGE = 16;
const GAP = 8;

// Delete grows out of the space the row leaves as it slides: nothing of it
// shows until there's room, and the bin fades in as the pill fills out
function DeleteAction({ drag, onPress }: { drag: SharedValue<number>; onPress: () => void }) {
  const { c } = useTheme();
  const pill = useAnimatedStyle(() => ({ width: Math.max(0, -drag.get() - EDGE - GAP) }));
  const bin = useAnimatedStyle(() => {
    const t = interpolate(-drag.get(), [EDGE + GAP + 20, ACTION_W], [0, 1], 'clamp');
    return { opacity: t, transform: [{ scale: 0.7 + t * 0.3 }] };
  });
  return (
    <Pressable accessibilityRole="button" accessibilityLabel="Видалити" onPress={onPress} style={styles.actionBox}>
      <Animated.View style={[styles.action, { backgroundColor: c.danger }, pill]}>
        <Animated.View style={bin}>
          <Icon name="trash" size={20} color={c.white} weight={2} />
        </Animated.View>
      </Animated.View>
    </Pressable>
  );
}

type Props = {
  title: string;
  when: string;
  selected: boolean;
  onOpen: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
};

// A past chat: a tap opens it, a swipe to the left shows delete, a long
// press turns the name into a field right where it is
export function ChatHistoryRow({ title, when, selected, onOpen, onRename, onDelete }: Props) {
  const { c } = useTheme();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);

  const edit = () => {
    hold();
    setDraft(title);
    setEditing(true);
  };
  const save = () => {
    setEditing(false);
    if (draft.trim() !== title) onRename(draft);
  };

  return (
    <ReanimatedSwipeable
      friction={1.6}
      rightThreshold={ACTION_W / 2}
      overshootRight={false}
      enabled={!editing}
      renderRightActions={(_progress, drag) => (
        <DeleteAction
          drag={drag}
          onPress={() => {
            thud();
            onDelete();
          }}
        />
      )}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ selected }}
        accessibilityHint="Утримуй, щоб перейменувати"
        accessibilityActions={[
          { name: 'longpress', label: 'Перейменувати' },
          { name: 'delete', label: 'Видалити' },
        ]}
        onAccessibilityAction={(e) => (e.nativeEvent.actionName === 'delete' ? onDelete() : edit())}
        onPress={() => {
          if (editing) return;
          tap();
          onOpen();
        }}
        onLongPress={edit}
        style={({ pressed }) => [styles.row, pressed && !editing && styles.pressed]}
      >
        <View style={styles.text}>
          {editing ? (
            <TextInput
              value={draft}
              onChangeText={setDraft}
              onSubmitEditing={save}
              onBlur={save}
              autoFocus
              selectTextOnFocus
              maxLength={TITLE_MAX}
              returnKeyType="done"
              selectionColor={c.accent}
              style={[styles.input, { color: c.ink }]}
              accessibilityLabel="Назва розмови"
            />
          ) : (
            <Text variant="rowTitle" numberOfLines={1}>
              {title}
            </Text>
          )}
          <Text variant="rowCaption" tone="faint">
            {when}
          </Text>
        </View>
        {selected && !editing ? <Icon name="check" size={18} color={c.accent} weight={2.2} /> : null}
      </Pressable>
    </ReanimatedSwipeable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12, paddingHorizontal: 20 },
  text: { flex: 1, gap: 2 },
  // the same box as the title, so nothing moves when it turns into a field
  input: { fontFamily: FONT.ui.semiBold, fontSize: 14, lineHeight: 19, padding: 0 },
  actionBox: { width: ACTION_W },
  action: {
    position: 'absolute',
    right: EDGE,
    top: 8,
    bottom: 8,
    borderRadius: 14,
    borderCurve: 'continuous',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  pressed: { opacity: 0.6 },
});
