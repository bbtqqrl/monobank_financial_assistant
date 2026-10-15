import { useFocusEffect } from 'expo-router';
import { useCallback } from 'react';

import { createStore } from '@/lib/store';

// whether the tab bar may shrink on scroll; read by the tabs layout
export const tabBarMinimizes = createStore(true);

// The bar only grows back when a list scrolls up. A screen that comes back
// already at the top (Overview after a long Transactions list) can't scroll
// up, so the bar would stay small. Turning minimizing off for a moment makes
// UIKit grow it, then it goes back to shrinking on scroll.
export function useExpandTabBarOnFocus() {
  useFocusEffect(
    useCallback(() => {
      tabBarMinimizes.set(false);
      const timer = setTimeout(() => tabBarMinimizes.set(true), 300);
      return () => {
        clearTimeout(timer);
        tabBarMinimizes.set(true);
      };
    }, []),
  );
}
