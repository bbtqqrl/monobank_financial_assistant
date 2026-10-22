import { useIsFocused } from 'expo-router';
import { useEffect, useRef } from 'react';
import { StyleSheet, useWindowDimensions, View } from 'react-native';

import { useTheme } from '@/theme';
import { FlowField, setFlowPalette, type Blob } from '@/ui/FlowField';

// Soft colour behind glass cards. Based on the Figma spots: blobs of the tab's
// colours that wander and melt into each other (see FlowField), busiest at the
// top, calm in the middle where the content sits.
//
// Each tab has its own tint. All screens share one palette and one clock, so
// going from one screen to another the colours morph and the blobs never jump;
// the colour flows only while visible and not at all with Reduce Motion.

export type BackdropVariant = 'warm' | 'green' | 'accent' | 'none';
type Tint = Exclude<BackdropVariant, 'none'>;

const WARM = '#C47C56';
const TEAL = '#4E8E8E';
const AMBER = '#D39B4E';
const GREEN = '#3E8A61';
const VIOLET = '#8A6FC8';
const SAND = '#B29E7E';

const DARK_STRENGTH = 0.78;

// the screen whose colours the shared palette shows right now
let paletteOwner: object | null = null;

// The same palette as flowing blobs: the two tint colours in the top corners,
// their mix wandering through the middle, sand and a bit of colour at the bottom
function blobsFor(tint: Tint, accent: string, aspect: number, strength: number): Blob[] {
  const [a, b, mix] =
    tint === 'warm' ? [WARM, TEAL, AMBER] : tint === 'green' ? [GREEN, WARM, TEAL] : [accent, VIOLET, WARM];
  const k = (op: number) => op * strength;
  return [
    { color: a, opacity: k(0.62), x: 0.0, y: 0.08, r: 0.7 },
    { color: b, opacity: k(0.56), x: 1.0, y: 0.22, r: 0.66 },
    { color: mix, opacity: k(0.34), x: 0.45, y: 0.62, r: 0.52 },
    { color: SAND, opacity: k(0.4), x: 0.25, y: aspect, r: 0.75 },
    { color: a, opacity: k(0.22), x: 1.0, y: aspect - 0.4, r: 0.55 },
  ];
}

// shared: a tab's own screen; the tabs draw one canvas under all of them, so
// this only steers the colours and stays see-through
export function Backdrop({ variant, shared = false }: { variant: BackdropVariant; shared?: boolean }) {
  const { c, dark } = useTheme();
  const { width, height } = useWindowDimensions();
  // screens stay mounted in tabs and stacks, no point animating the hidden ones
  const focused = useIsFocused();

  // The shared palette moves to this screen's colours when it comes into view.
  // A screen with its own canvas shown before keeps its last picture while
  // hidden and shows it for a frame on return, so there the colours switch at
  // once instead of morphing from the previous screen's and blinking.
  const shownBefore = useRef(false);
  const me = useRef({});
  useEffect(() => {
    // the screen under a sheet isn't focused but still shows: a theme switch
    // made in the sheet recolours it too, not only once the sheet is gone
    if ((!focused && paletteOwner !== me.current) || variant === 'none') return;
    setFlowPalette(
      c.bg,
      blobsFor(variant, c.accent, height / width, dark ? DARK_STRENGTH : 1),
      shared || !shownBefore.current,
    );
    shownBefore.current = true;
    paletteOwner = me.current;
  }, [focused, variant, shared, c.bg, c.accent, dark, width, height]);

  if (shared && variant !== 'none') return null;
  if (variant === 'none')
    return <View pointerEvents="none" style={[StyleSheet.absoluteFill, { backgroundColor: c.bg }]} />;
  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, { backgroundColor: c.bg }]}>
      <FlowField running={focused} />
    </View>
  );
}
