import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSyncExternalStore } from 'react';
import { Appearance } from 'react-native';

export type ThemePref = 'system' | 'light' | 'dark';

export const THEME_LABELS: Record<ThemePref, string> = {
  system: 'Як у системі',
  light: 'Світла',
  dark: 'Темна',
};

const KEY = 'theme';

let current: ThemePref = 'system';
const listeners = new Set<() => void>();

function apply(pref: ThemePref) {
  Appearance.setColorScheme(pref === 'system' ? 'unspecified' : pref);
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useThemePref(): ThemePref {
  return useSyncExternalStore(subscribe, () => current);
}

export function setThemePref(pref: ThemePref) {
  current = pref;
  apply(pref);
  listeners.forEach((l) => l());
  AsyncStorage.setItem(KEY, pref).catch(() => {});
}

// called once before the first screen so the app doesn't flash the wrong theme
export async function loadThemePref() {
  try {
    const saved = await AsyncStorage.getItem(KEY);
    if (saved === 'light' || saved === 'dark') setThemePref(saved);
  } catch {
    // keep the system theme
  }
}
