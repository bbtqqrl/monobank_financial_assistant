// The top of a value axis: the max rounded up to a number that still reads
// well halved (30 000, 40 000, 60 000, 80 000…)
export function niceTop(max: number) {
  if (max <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(max));
  const step = [1, 2, 3, 4, 5, 6, 8, 10].find((s) => s * power >= max) ?? 10;
  return step * power;
}

// Axis labels: "0", "500", "10 тис", "1,5 млн" (from hryvnias)
export function compactUah(uah: number) {
  const short = (v: number) => String(Math.round(v * 10) / 10).replace('.', ',');
  if (uah >= 1_000_000) return `${short(uah / 1_000_000)} млн`;
  if (uah >= 1_000) return `${short(uah / 1_000)} тис`;
  return String(Math.round(uah));
}

type Point = { x: number; y: number };

// A smooth line through the points that never bends past them (monotone
// cubic): a running total drawn this way never looks like it dipped.
export function smoothPath(points: Point[]) {
  const n = points.length;
  if (n === 0) return '';
  if (n === 1) return `M${points[0]!.x},${points[0]!.y}`;

  const dx = points.slice(1).map((p, i) => p.x - points[i]!.x);
  const slopes = points.slice(1).map((p, i) => (p.y - points[i]!.y) / (dx[i] || 1));
  const tangents = points.map((_, i) => {
    if (i === 0) return slopes[0]!;
    if (i === n - 1) return slopes[n - 2]!;
    const a = slopes[i - 1]!;
    const b = slopes[i]!;
    return a * b <= 0 ? 0 : (2 * a * b) / (a + b);
  });

  let d = `M${points[0]!.x},${points[0]!.y}`;
  for (let i = 0; i < n - 1; i++) {
    const p = points[i]!;
    const q = points[i + 1]!;
    const h = dx[i]! / 3;
    d += ` C${p.x + h},${p.y + tangents[i]! * h} ${q.x - h},${q.y - tangents[i + 1]! * h} ${q.x},${q.y}`;
  }
  return d;
}
