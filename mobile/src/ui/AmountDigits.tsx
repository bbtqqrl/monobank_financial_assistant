import { useEffect, useState } from 'react';
import { StyleSheet, View, type StyleProp, type TextStyle } from 'react-native';
import Animated, {
  Easing,
  Extrapolation,
  FadeIn,
  interpolate,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
  type AnimatedStyle,
} from 'react-native-reanimated';

type Props = {
  // as typed, "30005" or "12,5"; grouped here. Empty shows the placeholder
  text: string;
  style: StyleProp<AnimatedStyle<StyleProp<TextStyle>>>;
  placeholderStyle: StyleProp<TextStyle>;
};

// everything the amount can hold, measured once so a glyph can grow from nothing
const GLYPHS = [...'0123456789,'];
const SPACE = ' ';
const EASE = Easing.out(Easing.cubic);
const IN_MS = 320;
const OUT_MS = 220;

type CharProps = {
  char: string;
  // natural width; unknown until measured, or left out to swap with the placeholder
  width?: number;
  // a thousands gap in front of it
  gap: boolean;
  gapWidth: number;
  // typed now rather than there on open
  appear: boolean;
  leaving?: boolean;
  over?: boolean;
  style: Props['style'];
};

// One character. Its room opens before it shows and closes after it's gone, and a
// thousands gap moving to it opens the same way, so the amount slides instead of jumping.
function Char({ char, width, gap, gapWidth, appear, leaving, over, style }: CharProps) {
  const reduced = useReducedMotion();
  const shown = useSharedValue(leaving || !appear ? 1 : 0);
  const spaced = useSharedValue(gap ? 1 : 0);

  useEffect(() => {
    const to = leaving ? 0 : 1;
    shown.set(reduced ? to : withTiming(to, { duration: leaving ? OUT_MS : IN_MS, easing: EASE }));
  }, [leaving, reduced, shown]);

  useEffect(() => {
    const to = gap ? 1 : 0;
    spaced.set(reduced ? to : withTiming(to, { duration: IN_MS, easing: EASE }));
  }, [gap, reduced, spaced]);

  const box = useAnimatedStyle(() => {
    const p = shown.get();
    return {
      width: width === undefined ? undefined : width * p,
      marginLeft: spaced.get() * gapWidth,
      opacity: width === undefined ? p : interpolate(p, [0.4, 1], [0, 1], Extrapolation.CLAMP),
      transform: [{ translateY: (1 - p) * 6 }],
    };
  });

  return (
    <Animated.View style={[styles.char, over && styles.over, box]}>
      <Animated.Text style={[style, width !== undefined && { width }]} numberOfLines={1}>
        {char}
      </Animated.Text>
    </Animated.View>
  );
}

// "30005" → a gap before the 3rd digit from the end; the fraction has none
const hasGap = (i: number, wholeLength: number) => i > 0 && i < wholeLength && (wholeLength - i) % 3 === 0;

// the decimal-pad gives "." or "," depending on the region; it's shown as ","
const glyph = (char: string) => (char === '.' ? ',' : char);

// The big typed amount, one view per character keyed by its place, so typing or
// erasing only adds or drops the last one. What's there on open doesn't move.
export function AmountDigits({ text, style, placeholderStyle }: Props) {
  const [widths, setWidths] = useState<Record<string, number>>({});
  const [prev, setPrev] = useState(text);
  const [touched, setTouched] = useState(false);
  const [gone, setGone] = useState<{ id: number; char: string } | null>(null);

  if (text !== prev) {
    setPrev(text);
    setTouched(true);
    // the erased character stays a moment to fade out
    setGone(text.length < prev.length ? { id: (gone?.id ?? 0) + 1, char: glyph(prev.slice(-1)) } : null);
  }

  const chars = [...text].map(glyph);
  const comma = chars.indexOf(',');
  const whole = comma === -1 ? chars.length : comma;
  const gapWidth = widths[SPACE] ?? 0;

  return (
    <View style={styles.row}>
      {chars.map((char, i) => (
        <Char
          key={i}
          char={char}
          // the first digit takes the placeholder's place instead of opening room
          width={chars.length === 1 ? undefined : widths[char]}
          gap={hasGap(i, whole)}
          gapWidth={gapWidth}
          appear={touched}
          style={style}
        />
      ))}
      {text ? null : (
        <Animated.Text key={gone?.id ?? 0} entering={gone ? FadeIn.duration(IN_MS) : undefined} style={placeholderStyle}>
          0
        </Animated.Text>
      )}
      {gone ? (
        <Char
          key={`gone-${gone.id}`}
          char={gone.char}
          width={text ? widths[gone.char] : undefined}
          gap={false}
          gapWidth={gapWidth}
          appear={false}
          leaving
          // the very last one fades over the placeholder
          over={!text}
          style={style}
        />
      ) : null}

      <View pointerEvents="none" style={styles.measure}>
        {[...GLYPHS, SPACE].map((g) => (
          <Animated.Text
            key={g}
            style={style}
            onLayout={(e) => {
              const w = e.nativeEvent.layout.width;
              setWidths((all) => (all[g] === w ? all : { ...all, [g]: w }));
            }}
          >
            {g}
          </Animated.Text>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  // its own row: the parent's gap would split the digits
  row: { flexDirection: 'row', alignItems: 'center' },
  char: { overflow: 'hidden', alignItems: 'center' },
  over: { position: 'absolute', left: 0 },
  measure: { position: 'absolute', top: 0, left: 0, width: 1000, flexDirection: 'row', opacity: 0 },
});
