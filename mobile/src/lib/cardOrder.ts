import AsyncStorage from '@react-native-async-storage/async-storage';
import { z } from 'zod';

import { createStore } from '@/lib/store';

const KEY = 'cardOrder';

// account ids in the order the user arranged them; null keeps the bank's order
export const cardOrder = createStore<readonly number[] | null>(null);

export function saveCardOrder(ids: readonly number[] | null) {
  cardOrder.set(ids);
  (ids ? AsyncStorage.setItem(KEY, JSON.stringify(ids)) : AsyncStorage.removeItem(KEY)).catch(() => {});
}

// read once on start, next to the theme
export async function loadCardOrder() {
  try {
    const saved = await AsyncStorage.getItem(KEY);
    if (!saved) return;
    const parsed = z.array(z.number().int()).safeParse(JSON.parse(saved));
    if (parsed.success) cardOrder.set(parsed.data);
  } catch {
  }
}
