// Generated from the design (figma-plugin PATHS), don't edit by hand.
// 24×24 stroke icons.

type Shape =
  | readonly ['path', { readonly d: string }]
  | readonly ['circle', { readonly cx: number; readonly cy: number; readonly r: number }]
  | readonly ['rect', { readonly x: number; readonly y: number; readonly width: number; readonly height: number; readonly rx?: number }];

export const ICONS = {
  menu: [
    ['path', { d: 'M4 7h16M4 12h11M4 17h7' }],
  ],
  person: [
    ['circle', { cx: 12, cy: 8.2, r: 3.6 }],
    ['path', { d: 'M5.2 20a6.8 6.8 0 0 1 13.6 0' }],
  ],
  bell: [
    ['path', { d: 'M18 8a6 6 0 1 0-12 0c0 6-2 7-2 7h16s-2-1-2-7' }],
    ['path', { d: 'M10.5 19a2 2 0 0 0 3 0' }],
  ],
  eye: [
    ['path', { d: 'M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z' }],
    ['circle', { cx: 12, cy: 12, r: 2.6 }],
  ],
  arrowDown: [
    ['path', { d: 'M12 5v14M6 13l6 6 6-6' }],
  ],
  arrowUp: [
    ['path', { d: 'M12 19V5M6 11l6-6 6 6' }],
  ],
  income: [
    ['path', { d: 'M12 4v16M18 10l-6-6-6 6' }],
  ],
  cart: [
    ['path', { d: 'M4 5h2l2.3 10.2a1.6 1.6 0 0 0 1.6 1.3h7.4a1.6 1.6 0 0 0 1.6-1.2L20.5 8H7' }],
    ['circle', { cx: 10, cy: 20, r: 1.1 }],
    ['circle', { cx: 17.5, cy: 20, r: 1.1 }],
  ],
  bus: [
    ['path', { d: 'M5 16.5V7a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v9.5' }],
    ['path', { d: 'M5 11h14' }],
    ['circle', { cx: 8, cy: 16.5, r: 1.2 }],
    ['circle', { cx: 16, cy: 16.5, r: 1.2 }],
    ['path', { d: 'M7 19v1.4M17 19v1.4' }],
  ],
  laptop: [
    ['rect', { x: 3, y: 5, width: 18, height: 12, rx: 2 }],
    ['path', { d: 'M8 20h8M12 17v3' }],
  ],
  sparkle: [
    ['path', { d: 'M12 3.5 14 9l5.5 2-5.5 2L12 18.5 10 13l-5.5-2L10 9Z' }],
  ],
  homeSolid: [
    ['path', { d: 'M4 10.6 12 4l8 6.6V19a1 1 0 0 1-1 1h-4v-5h-6v5H5a1 1 0 0 1-1-1Z' }],
  ],
  home: [
    ['path', { d: 'M4 10.6 12 4l8 6.6V19a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1Z' }],
  ],
  list: [
    ['rect', { x: 4, y: 3.5, width: 16, height: 17, rx: 3 }],
    ['path', { d: 'M8 9h8M8 13h8M8 17h4' }],
  ],
  chart: [
    ['path', { d: 'M5 19V11M12 19V5M19 19v-5' }],
  ],
  star: [
    ['path', { d: 'M12 3.2 14.3 9 20 11.3 14.3 13.6 12 19.4 9.7 13.6 4 11.3 9.7 9Z' }],
  ],
  plus: [
    ['path', { d: 'M12 5v14M5 12h14' }],
  ],
  search: [
    ['circle', { cx: 11, cy: 11, r: 6.6 }],
    ['path', { d: 'M16 16l4 4' }],
  ],
  filter: [
    ['path', { d: 'M4 7h16M7 12h10M10 17h4' }],
  ],
  card: [
    ['rect', { x: 2.5, y: 5, width: 19, height: 14, rx: 3 }],
    ['path', { d: 'M2.5 10h19' }],
  ],
  chevronDown: [
    ['path', { d: 'M7 10l5 5 5-5' }],
  ],
  chevronRight: [
    ['path', { d: 'M10 6l6 6-6 6' }],
  ],
  chevronLeft: [
    ['path', { d: 'M14 6l-6 6 6 6' }],
  ],
  dots: [
    ['path', { d: 'M6 12h.01M12 12h.01M18 12h.01' }],
  ],
  share: [
    ['path', { d: 'M12 15V4' }],
    ['path', { d: 'M8 8l4-4 4 4' }],
    ['path', { d: 'M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4' }],
  ],
  gear: [
    ['circle', { cx: 12, cy: 12, r: 3.2 }],
    ['path', { d: 'M4.5 12a7.5 7.5 0 0 1 .1-1.2l-2-1.5 2-3.4 2.3.9a7.6 7.6 0 0 1 2-1.2l.4-2.4h4l.4 2.4a7.6 7.6 0 0 1 2 1.2l2.3-.9 2 3.4-2 1.5a7.5 7.5 0 0 1 0 2.4l2 1.5-2 3.4-2.3-.9a7.6 7.6 0 0 1-2 1.2l-.4 2.4h-4l-.4-2.4a7.6 7.6 0 0 1-2-1.2l-2.3.9-2-3.4 2-1.5A7.5 7.5 0 0 1 4.5 12Z' }],
  ],
  refresh: [
    ['path', { d: 'M20 11a8 8 0 0 0-13.7-5.3L4 8' }],
    ['path', { d: 'M4 4v4h4' }],
    ['path', { d: 'M4 13a8 8 0 0 0 13.7 5.3L20 16' }],
    ['path', { d: 'M20 20v-4h-4' }],
  ],
  lock: [
    ['rect', { x: 4, y: 10, width: 16, height: 10, rx: 2 }],
    ['path', { d: 'M8 10V7a4 4 0 0 1 8 0v3' }],
  ],
  sun: [
    ['circle', { cx: 12, cy: 12, r: 4.2 }],
    ['path', { d: 'M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4' }],
  ],
  logout: [
    ['path', { d: 'M15 17l5-5-5-5' }],
    ['path', { d: 'M20 12H9' }],
    ['path', { d: 'M12 20H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6' }],
  ],
  jar: [
    ['path', { d: 'M6 8h12l-1 11a2 2 0 0 1-2 1.8H9A2 2 0 0 1 7 19Z' }],
    ['path', { d: 'M9 8V6a3 3 0 0 1 6 0v2' }],
  ],
  health: [
    ['path', { d: 'M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6Z' }],
  ],
  pencil: [
    ['path', { d: 'M4 20h4l10-10-4-4L4 16Z' }],
    ['path', { d: 'M14 6l4 4' }],
  ],
  repeat: [
    ['path', { d: 'M20 7H9a4 4 0 0 0 0 8h6a4 4 0 0 1 0 8H4' }],
    ['path', { d: 'M17 4l3 3-3 3' }],
  ],
  close: [
    ['path', { d: 'M6 6l12 12M18 6 6 18' }],
  ],
  expand: [
    ['path', { d: 'M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7' }],
  ],
  map: [
    ['path', { d: 'M9 4 3.5 6v14L9 18l6 2 5.5-2V4L15 6Z' }],
    ['path', { d: 'M9 4v14M15 6v14' }],
  ],
  budget: [
    ['path', { d: 'M4 16.5a8 8 0 1 1 16 0' }],
    ['path', { d: 'M12 16.5l3.6-4.6' }],
    ['circle', { cx: 12, cy: 16.5, r: 1.2 }],
  ],
  locate: [
    ['circle', { cx: 12, cy: 12, r: 6.5 }],
    ['circle', { cx: 12, cy: 12, r: 2.2 }],
    ['path', { d: 'M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3' }],
  ],
  check: [
    ['path', { d: 'M5 12.5l4.5 4.5L19 7.5' }],
  ],
  food: [
    ['path', { d: 'M7 3v6.5a2 2 0 0 0 4 0V3' }],
    ['path', { d: 'M9 9.5V21' }],
    ['path', { d: 'M16.4 3.4c1.8 1.9 2.4 5.2 1.2 7.6h-1.2Z' }],
    ['path', { d: 'M17 11v10' }],
  ],
  taxi: [
    ['path', { d: 'M4 16v-3l1.7-4.2A2 2 0 0 1 7.6 7.5h8.8a2 2 0 0 1 1.9 1.3L20 13v3Z' }],
    ['path', { d: 'M4 13h16' }],
    ['circle', { cx: 7.5, cy: 16, r: 1.2 }],
    ['circle', { cx: 16.5, cy: 16, r: 1.2 }],
    ['path', { d: 'M6 18.4v1.6M18 18.4v1.6' }],
  ],
  fuel: [
    ['path', { d: 'M4.5 20V6a2 2 0 0 1 2-2h4.5a2 2 0 0 1 2 2v14' }],
    ['path', { d: 'M3 20h11.5' }],
    ['path', { d: 'M13 10.5h3a1.5 1.5 0 0 1 1.5 1.5v4a1.5 1.5 0 0 0 3 0V9l-2.4-2.4' }],
    ['path', { d: 'M6.8 8h4' }],
  ],
  utilities: [
    ['path', { d: 'M9 3v5M15 3v5' }],
    ['path', { d: 'M6 8h12v3a6 6 0 0 1-12 0Z' }],
    ['path', { d: 'M12 17v4' }],
  ],
  travel: [
    ['path', { d: 'M21 4 3 11l7 3 3 7Z' }],
    ['path', { d: 'M21 4 10 14' }],
  ],
  pets: [
    ['circle', { cx: 8, cy: 7.5, r: 1.9 }],
    ['circle', { cx: 16, cy: 7.5, r: 1.9 }],
    ['circle', { cx: 4.6, cy: 12.6, r: 1.7 }],
    ['circle', { cx: 19.4, cy: 12.6, r: 1.7 }],
    ['path', { d: 'M12 12.5c2.7 0 4.9 2.2 4.9 4.3 0 2.2-2.2 3.8-4.9 3.8s-4.9-1.6-4.9-3.8c0-2.1 2.2-4.3 4.9-4.3Z' }],
  ],
  books: [
    ['path', { d: 'M5 4.6A1.6 1.6 0 0 1 6.6 3H19v15H6.6A1.6 1.6 0 0 0 5 19.6Z' }],
    ['path', { d: 'M5 19.6A1.6 1.6 0 0 1 6.6 21H19' }],
  ],
  repair: [
    ['path', { d: 'M15.4 3.4a5 5 0 0 0-5.8 6.2L3.6 15.6a2 2 0 0 0 2.8 2.8l6-6a5 5 0 0 0 6.2-5.8L15.9 9.4l-2.4-.5-.5-2.4Z' }],
  ],
  shirt: [
    ['path', { d: 'M9 4 5 6.5V11h2.5v9h9v-9H19V6.5L15 4a3 3 0 0 1-6 0Z' }],
  ],
  game: [
    ['rect', { x: 2.5, y: 7.5, width: 19, height: 9, rx: 4.5 }],
    ['path', { d: 'M7 10v3M5.5 11.5h3' }],
    ['circle', { cx: 16, cy: 11, r: 0.9 }],
    ['circle', { cx: 18.4, cy: 13, r: 0.9 }],
  ],
} as const satisfies Record<string, readonly Shape[]>;

export type IconName = keyof typeof ICONS;
