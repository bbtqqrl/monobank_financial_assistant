import { useEffect, useState } from 'react';
import { StyleSheet, useWindowDimensions, View } from 'react-native';
import Animated, {
  cancelAnimation,
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Defs, Ellipse, RadialGradient, Stop } from 'react-native-svg';

import { useTheme } from '@/theme';

// Soft colour fields behind glass cards. Based on the Figma spots, but
// bigger and overlapping at the top, so while they drift the colours blend
// into each other (think Revolut's backgrounds); the middle of the screen
// stays calm for content. A blur filter would be expensive, so each field is
// a radial gradient with a long soft falloff.
//
// Each tab has its own tint. Switching tints crossfades the layers; fields
// drift only while visible and not at all with Reduce Motion.

export type BackdropVariant = 'warm' | 'green' | 'accent' | 'none';
type Tint = Exclude<BackdropVariant, 'none'>;

type Spot = { w: number; h: number; x: number; y: number; color: string; op: number };

const WARM = '#C47C56';
const TEAL = '#4E8E8E';
const AMBER = '#D39B4E';
const GREEN = '#3E8A61';
const VIOLET = '#8A6FC8';
const SAND = '#B29E7E';

// coordinates in the 390×844 design frame
function spotsFor(tint: Tint, accent: string): Spot[] {
  const [a, b, mix] =
    tint === 'warm' ? [WARM, TEAL, AMBER] : tint === 'green' ? [GREEN, WARM, TEAL] : [accent, VIOLET, WARM];
  return [
    { w: 560, h: 500, x: -250, y: -250, color: a, op: 0.38 },
    { w: 500, h: 470, x: 120, y: -190, color: b, op: 0.34 },
    // wanders between the two top fields and mixes them
    { w: 420, h: 380, x: -60, y: 90, color: mix, op: 0.2 },
    { w: 520, h: 360, x: -60, y: 700, color: SAND, op: 0.28 },
  ];
}

const DESIGN_W = 390;
const DESIGN_H = 844;
const SOFT = 110;
const FADE_MS = 700;
const DARK_STRENGTH = 0.55;
// x and y run on different periods, so each field wanders along a curve
// and the four never line up into a visible loop
const DRIFT = [
  { dx: 140, dy: 90, xMs: 11000, yMs: 9000, sMs: 13000 },
  { dx: -130, dy: 110, xMs: 9500, yMs: 12500, sMs: 10000 },
  { dx: 180, dy: 140, xMs: 14000, yMs: 10500, sMs: 12000 },
  { dx: -90, dy: 40, xMs: 12000, yMs: 15000, sMs: 11000 },
];

// top fields stay pinned to the top, the bottom one to the bottom of the screen
function geometry(s: Spot, width: number, height: number) {
  const k = width / DESIGN_W;
  const rx = (s.w / 2) * k;
  const ry = (s.h / 2) * k;
  const cx = (s.x + s.w / 2) * k;
  const cyDesign = (s.y + s.h / 2) * k;
  const cy = s.y > DESIGN_H / 2 ? height - (DESIGN_H * k - cyDesign) : cyDesign;
  const r = rx + SOFT;
  return { cx, cy, rx: r, ry: ry + SOFT, core: Math.max(0, rx - SOFT) / r, edge: rx / r };
}

type SpotProps = { id: string; spot: Spot; index: number; strength: number; running: boolean };

function SpotView({ id, spot, index, strength, running }: SpotProps) {
  const { width, height } = useWindowDimensions();
  const reduceMotion = useReducedMotion();
  const tx = useSharedValue(0);
  const ty = useSharedValue(0);
  const ts = useSharedValue(0);
  const drift = DRIFT[index % DRIFT.length]!;
  const g = geometry(spot, width, height);
  const op = spot.op * strength;

  useEffect(() => {
    if (!running || reduceMotion) return;
    const wave = (ms: number) =>
      withRepeat(withTiming(1, { duration: ms, easing: Easing.inOut(Easing.sin) }), -1, true);
    tx.value = wave(drift.xMs);
    ty.value = wave(drift.yMs);
    ts.value = wave(drift.sMs);
    return () => {
      cancelAnimation(tx);
      cancelAnimation(ty);
      cancelAnimation(ts);
    };
  }, [running, reduceMotion, drift, tx, ty, ts]);

  const style = useAnimatedStyle(() => ({
    transform: [
      { translateX: (tx.value - 0.5) * drift.dx },
      { translateY: (ty.value - 0.5) * drift.dy },
      { scale: 1 + ts.value * 0.18 },
    ],
  }));

  return (
    <Animated.View
      style={[{ position: 'absolute', left: g.cx - g.rx, top: g.cy - g.ry, width: g.rx * 2, height: g.ry * 2 }, style]}
    >
      <Svg width={g.rx * 2} height={g.ry * 2}>
        <Defs>
          <RadialGradient id={id} cx={g.rx} cy={g.ry} rx={g.rx} ry={g.ry} gradientUnits="userSpaceOnUse">
            <Stop offset={0} stopColor={spot.color} stopOpacity={op} />
            <Stop offset={g.core} stopColor={spot.color} stopOpacity={op * 0.9} />
            <Stop offset={g.edge} stopColor={spot.color} stopOpacity={op * 0.45} />
            <Stop offset={1} stopColor={spot.color} stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Ellipse cx={g.rx} cy={g.ry} rx={g.rx} ry={g.ry} fill={`url(#${id})`} />
      </Svg>
    </Animated.View>
  );
}

function Layer({ tint, active }: { tint: Tint; active: boolean }) {
  const { c, dark } = useTheme();
  const shown = useSharedValue(0);

  useEffect(() => {
    shown.value = withTiming(active ? 1 : 0, { duration: FADE_MS, easing: Easing.inOut(Easing.cubic) });
  }, [active, shown]);

  // the incoming tint also "breathes in" a little
  const style = useAnimatedStyle(() => ({
    opacity: shown.value,
    transform: [{ scale: 0.96 + shown.value * 0.04 }],
  }));

  return (
    <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, style]}>
      {spotsFor(tint, c.accent).map((spot, i) => (
        <SpotView key={i} id={`${tint}${i}`} spot={spot} index={i} strength={dark ? DARK_STRENGTH : 1} running={active} />
      ))}
    </Animated.View>
  );
}

export function Backdrop({ variant }: { variant: BackdropVariant }) {
  const { c } = useTheme();
  // layers mount the first time their tint is needed and stay for crossfades
  const [mounted, setMounted] = useState<Tint[]>([]);
  if (variant !== 'none' && !mounted.includes(variant)) setMounted([...mounted, variant]);

  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, { backgroundColor: c.bg }]}>
      {mounted.map((tint) => (
        <Layer key={tint} tint={tint} active={tint === variant} />
      ))}
    </View>
  );
}
