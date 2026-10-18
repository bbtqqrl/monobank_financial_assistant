import { Canvas, Fill, Shader, Skia } from '@shopify/react-native-skia';
import { useEffect } from 'react';
import { StyleSheet, useWindowDimensions } from 'react-native';
import {
  Easing,
  makeMutable,
  useDerivedValue,
  useFrameCallback,
  useReducedMotion,
  withTiming,
} from 'react-native-reanimated';

// A colour that flows: soft blobs of colour wander slowly over the base and melt
// into each other, like iOS's mesh gradients. Drawn by one shader on the UI thread.
const SOURCE = Skia.RuntimeEffect.Make(`
uniform float2 res;
uniform float t;
uniform float4 base;
uniform float4 c0; uniform float4 c1; uniform float4 c2; uniform float4 c3; uniform float4 c4;
uniform float3 b0; uniform float3 b1; uniform float3 b2; uniform float3 b3; uniform float3 b4;

// where a blob is now: its home plus two slow sines on different periods
float2 at(float3 b, float k) {
  return b.xy + float2(sin(t * (0.00034 + 0.00006 * k) + k * 1.7), cos(t * (0.00027 + 0.00005 * k) + k * 2.3)) * 0.24;
}

float3 blend(float3 col, float4 c, float3 b, float k, float2 uv) {
  float2 d = uv - at(b, k);
  float w = exp(-dot(d, d) / (b.z * b.z)) * c.a;
  return mix(col, c.rgb, w);
}

half4 main(float2 xy) {
  // widths are 1, heights follow the screen, so blobs stay round
  float2 uv = xy / res.x;
  float3 col = base.rgb;
  col = blend(col, c4, b4, 4.0, uv);
  col = blend(col, c0, b0, 0.0, uv);
  col = blend(col, c1, b1, 1.0, uv);
  col = blend(col, c2, b2, 2.0, uv);
  col = blend(col, c3, b3, 3.0, uv);
  return half4(half3(col), 1.0);
}`)!;

export type Blob = {
  // '#RRGGBB'
  color: string;
  opacity: number;
  // home, in screen widths from the top-left
  x: number;
  y: number;
  // soft radius, in screen widths
  r: number;
};

const BLOBS = 5;
const MORPH_MS = 650;
// the blobs move a few points a second: 30 frames are plenty, and on a 120 Hz
// screen it's a quarter of the redraws
const FRAME_MS = 1000 / 30;

const rgba = (hex: string, a = 1) => {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, a];
};

// base rgba, then per blob rgba + x, y, r
function flatten(base: string, blobs: Blob[]): number[] {
  return [...rgba(base), ...blobs.slice(0, BLOBS).flatMap((b) => [...rgba(b.color, b.opacity), b.x, b.y, b.r])];
}

// One clock and one palette for every screen: a screen coming in shows exactly
// what the one going out showed, then the colours move to its own.
const clock = makeMutable(0);
const from = makeMutable<number[]>([]);
const to = makeMutable<number[]>([]);
const morph = makeMutable(1);

// the colours every backdrop flows towards; the change itself is animated
export function setFlowPalette(base: string, blobs: Blob[], animate = true) {
  const target = flatten(base, blobs);
  const start = to.value.length ? mixNumbers(from.value, to.value, morph.value) : target;
  from.value = start;
  to.value = target;
  morph.value = 0;
  morph.value = animate ? withTiming(1, { duration: MORPH_MS, easing: Easing.inOut(Easing.cubic) }) : 1;
}

function mixNumbers(a: number[], b: number[], p: number) {
  'worklet';
  if (a.length !== b.length) return b;
  return b.map((v, i) => a[i]! + (v - a[i]!) * p);
}

function uniformsFrom(v: number[], width: number, height: number, t: number) {
  'worklet';
  const u: Record<string, number | number[]> = { res: [width, height], t, base: v.slice(0, 4) };
  for (let i = 0; i < BLOBS; i++) {
    const o = 4 + i * 7;
    u[`c${i}`] = v.slice(o, o + 4);
    u[`b${i}`] = v.slice(o + 4, o + 7);
  }
  return u;
}

type Props = {
  // its own fixed colours instead of the shared palette (the lock screen)
  base?: string;
  blobs?: Blob[];
  running: boolean;
};

export function FlowField({ base, blobs, running }: Props) {
  const { width, height } = useWindowDimensions();
  const reduced = useReducedMotion();

  const frame = useFrameCallback((info) => {
    // a little early still counts, or 60 Hz frames would land on 20 fps
    if (info.timestamp - clock.value < FRAME_MS - 4) return;
    clock.value = info.timestamp;
  }, false);

  useEffect(() => {
    frame.setActive(running && !reduced);
  }, [running, reduced, frame]);

  const own = base && blobs ? flatten(base, blobs) : null;
  const uniforms = useDerivedValue(() => {
    const v = own ?? mixNumbers(from.value, to.value, morph.value);
    return uniformsFrom(v.length ? v : new Array(4 + BLOBS * 7).fill(0), width, height, clock.value);
  });

  return (
    <Canvas style={StyleSheet.absoluteFill} pointerEvents="none">
      <Fill>
        <Shader source={SOURCE} uniforms={uniforms} />
      </Fill>
    </Canvas>
  );
}
