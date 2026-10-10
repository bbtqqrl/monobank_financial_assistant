// Pull-to-refresh, done by hand on iOS.
//
// The system RefreshControl doesn't fit here: its spinner sits under the
// scrolling backdrop (see ScrollBackdrop), it starts the refresh mid-pull, and
// it misses quick flicks. So the pull is read from the scroll events instead:
//
//   pulling past PULL_AT   the indicator takes the accent
//   letting go past it     nothing yet, the content bounces back as usual
//   back at rest           a buzz, the refresh starts and the header says so
//
// Nothing else happens while a finger is down or the content moves: a render
// costs frames, and so does a buzz (expo-haptics wakes the Taptic Engine on
// the main thread every time). For the same reason the refresh status lives in
// a store only the header reads, so the screen itself never re-renders for it.
//
// usePullRefresh runs the refresh and holds its status, usePullScroll is the
// scroll handler that reads the pull, PullIndicator draws it. Android keeps
// RefreshControl, its lists don't stretch past the edge.

import { useCallback, useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Platform } from 'react-native';
import { useAnimatedScrollHandler, useSharedValue, type SharedValue } from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';

import { thud } from '@/lib/haptics';
import { createStore, type Store } from '@/lib/store';
import type { Flash } from '@/lib/useFlash';

// pulled this far down, letting go refreshes
export const PULL_AT = 80;

// what the header shows in place of the title: the refresh running, then for
// a moment how it went
export type RefreshStatus = 'busy' | Flash | null;

const UPDATED: Flash = { ok: true, text: 'Оновлено' };
const FAILED: Flash = { ok: false, text: 'Не вдалося оновити' };
const FLASH_MS = 2200;

export type PullRefresh = { status: Store<RefreshStatus>; start: () => void };

// Runs the refresh, one at a time. run resolves with what to tell the user
// (a plain "Оновлено" when it says nothing) or rejects.
export function usePullRefresh(run: () => Promise<Flash | void>): PullRefresh {
  const [status] = useState(() => createStore<RefreshStatus>(null));
  const busy = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  // start stays the same function: the scroll handler that calls it is rebuilt
  // whenever it changes, and a rebuild mid-scroll drops frames
  const latest = useRef(run);
  useEffect(() => {
    latest.current = run;
  });
  useEffect(() => () => clearTimeout(timer.current), []);

  const start = useCallback(() => {
    if (busy.current) return;
    busy.current = true;
    clearTimeout(timer.current);
    thud();
    status.set('busy');
    latest
      .current()
      .then((flash) => flash ?? UPDATED, () => FAILED)
      .then((flash) => {
        busy.current = false;
        status.set(flash);
        AccessibilityInfo.announceForAccessibility(flash.text);
        timer.current = setTimeout(() => status.set(null), FLASH_MS);
      });
  }, [status]);

  return { status, start };
}

type ScrollOptions = {
  // gets contentOffset.y
  offset: SharedValue<number>;
  // contentOffset.y when nothing is pulled
  rest: number;
  pull?: PullRefresh;
  // one more place for the offset, for whoever reacts to scrolling
  mirror?: SharedValue<number>;
};

// The screen's scroll handler, reading the pull as described above
export function usePullScroll({ offset, rest, pull, mirror }: ScrollOptions) {
  const dragging = useSharedValue(false);
  // let go past the line, waiting for the content to come to rest
  const pending = useSharedValue(false);
  const start = Platform.OS === 'ios' ? pull?.start : undefined;

  return useAnimatedScrollHandler({
    onScroll: (e) => {
      const y = e.contentOffset.y;
      offset.set(y);
      mirror?.set(y);
      if (start && pending.get() && !dragging.get() && y >= rest - 1) {
        pending.set(false);
        scheduleOnRN(start);
      }
    },
    onBeginDrag: () => {
      dragging.set(true);
    },
    onEndDrag: (e) => {
      dragging.set(false);
      if (start && rest - e.contentOffset.y >= PULL_AT) pending.set(true);
    },
    // the bounce's last scroll event can be throttled away. This also fires
    // when a finger catches the content mid-bounce, so it checks for rest too.
    onMomentumEnd: (e) => {
      if (start && pending.get() && !dragging.get() && e.contentOffset.y >= rest - 1) {
        pending.set(false);
        scheduleOnRN(start);
      }
    },
  });
}
