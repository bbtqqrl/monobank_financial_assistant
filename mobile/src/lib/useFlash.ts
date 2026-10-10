import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

export type Flash = { ok: boolean; text: string };

const SHOW_MS = 2200;

// A short note that clears itself, like what a refresh just did
export function useFlash() {
  const [flash, setFlash] = useState<Flash | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => () => clearTimeout(timer.current), []);

  const show = (next: Flash) => {
    setFlash(next);
    AccessibilityInfo.announceForAccessibility(next.text);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setFlash(null), SHOW_MS);
  };

  return [flash, show] as const;
}
