import { captureScreen, releaseCapture } from 'react-native-view-shot';

import { createStore } from '@/lib/store';
import { getThemePref, setThemePref, type ThemePref } from '@/theme/preference';

export type ThemeShot = { uri: string; pref: ThemePref };

// a picture of the screen as it was, laid over the app while the theme changes
// under it (see ThemeFade)
export const themeShot = createStore<ThemeShot | null>(null);

// the last pick, not applied yet: the picker shows it at once
export const themeTarget = createStore<ThemePref | null>(null);

// a change is running: its picture is being taken or fading
let busy = false;

// Some parts change theme at once (text, cards, the native sheet) and some
// flow over (the backdrop): switching under a still picture of the old screen
// and fading that out makes it one even change. Picks made while one runs
// wait for it; only the last of them is applied, as one more such change.
export function switchTheme(pref: ThemePref) {
  themeTarget.set(pref);
  if (!busy) next();
}

async function next() {
  const pref = themeTarget.get();
  if (!pref || pref === getThemePref()) {
    themeTarget.set(null);
    return;
  }
  busy = true;
  try {
    const uri = await captureScreen({ format: 'jpg', quality: 0.92, result: 'tmpfile' });
    themeShot.set({ uri, pref });
  } catch {
    setThemePref(pref);
    busy = false;
    next();
  }
}

// ThemeFade is done with a picture: on to the latest pick, if there is one
export function themeFadeDone(uri: string) {
  themeShot.set(null);
  releaseCapture(uri);
  busy = false;
  next();
}
