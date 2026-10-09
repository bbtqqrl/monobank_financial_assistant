import { useEffect, useMemo, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  useAnimatedReaction,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  type SharedValue,
} from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';

import { tap, thud } from '@/lib/haptics';

type Props<T> = {
  items: T[];
  keyOf: (item: T) => number;
  // every row is this tall, gaps included
  rowHeight: number;
  renderRow: (item: T) => ReactNode;
  onChange: (items: T[]) => void;
};

// key → slot, shared by every row while one of them is dragged
type Slots = Record<string, number>;

const SPRING = { duration: 320, dampingRatio: 0.85 };
// a hold before the drag, so a plain swipe still moves the sheet
const HOLD_MS = 220;

const slotsOf = <T,>(items: T[], keyOf: (item: T) => number): Slots =>
  Object.fromEntries(items.map((item, i) => [String(keyOf(item)), i]));

// A list reordered by holding a row and dragging it; the others make room
export function SortableList<T>({ items, keyOf, rowHeight, renderRow, onChange }: Props<T>) {
  const slots = useSharedValue<Slots>(slotsOf(items, keyOf));

  // a new list from outside (saved order, reset) puts everyone back in place
  useEffect(() => {
    slots.set(slotsOf(items, keyOf));
  }, [items, keyOf, slots]);

  const drop = (next: Slots) => {
    const sorted = [...items].sort((a, b) => (next[String(keyOf(a))] ?? 0) - (next[String(keyOf(b))] ?? 0));
    if (sorted.some((item, i) => item !== items[i])) onChange(sorted);
  };

  return (
    <View style={{ height: items.length * rowHeight }}>
      {items.map((item) => (
        <Row key={keyOf(item)} id={String(keyOf(item))} slots={slots} count={items.length} rowHeight={rowHeight} onDrop={drop}>
          {renderRow(item)}
        </Row>
      ))}
    </View>
  );
}

function Row({ id, slots, count, rowHeight, onDrop, children }: {
  id: string;
  slots: SharedValue<Slots>;
  count: number;
  rowHeight: number;
  onDrop: (slots: Slots) => void;
  children: ReactNode;
}) {
  const y = useSharedValue((slots.get()[id] ?? 0) * rowHeight);
  const dragging = useSharedValue(false);
  const from = useSharedValue(0);

  // follow the slot while another row is dragged past this one
  useAnimatedReaction(
    () => slots.get()[id] ?? 0,
    (slot, before) => {
      if (slot !== before && !dragging.get()) y.set(withSpring(slot * rowHeight, SPRING));
    },
  );

  const pan = useMemo(
    () =>
      Gesture.Pan()
        .activateAfterLongPress(HOLD_MS)
        .onStart(() => {
          dragging.set(true);
          from.set(y.get());
          scheduleOnRN(thud);
        })
        .onUpdate((e) => {
          const next = Math.min(Math.max(from.get() + e.translationY, 0), (count - 1) * rowHeight);
          y.set(next);
          const to = Math.round(next / rowHeight);
          const now = slots.get();
          const at = now[id] ?? 0;
          if (to === at) return;
          // the row sitting in the new slot takes the old one
          const swapped: Slots = { ...now, [id]: to };
          for (const key in now) if (key !== id && now[key] === to) swapped[key] = at;
          slots.set(swapped);
          scheduleOnRN(tap);
        })
        .onFinalize(() => {
          if (!dragging.get()) return;
          dragging.set(false);
          y.set(withSpring((slots.get()[id] ?? 0) * rowHeight, SPRING));
          scheduleOnRN(onDrop, slots.get());
        }),
    [count, dragging, from, id, onDrop, rowHeight, slots, y],
  );

  const style = useAnimatedStyle(() => ({
    zIndex: dragging.get() ? 1 : 0,
    transform: [{ translateY: y.get() }, { scale: withSpring(dragging.get() ? 1.03 : 1, SPRING) }],
  }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={[styles.row, { height: rowHeight }, style]}>{children}</Animated.View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  row: { position: 'absolute', left: 0, right: 0, top: 0 },
});
