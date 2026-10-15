import AsyncStorage from '@react-native-async-storage/async-storage';
import { z } from 'zod';

import { createStore } from '@/lib/store';

const ORDER_KEY = 'cardOrder';
const HIDDEN_KEY = 'hiddenCards';
const BALANCE_HIDDEN_KEY = 'balanceHidden';

const Ids = z.array(z.number().int());

// account ids in the order the user arranged them; null keeps the bank's order
export const cardOrder = createStore<readonly number[] | null>(null);

// account ids left out of the Overview and the account pickers
export const hiddenCards = createStore<readonly number[]>([]);

// balances shown as dots on every card, so nobody reads them over a shoulder
export const balanceHidden = createStore(false);

export function setBalanceHidden(hidden: boolean) {
  balanceHidden.set(hidden);
  (hidden ? AsyncStorage.setItem(BALANCE_HIDDEN_KEY, '1') : AsyncStorage.removeItem(BALANCE_HIDDEN_KEY)).catch(() => {});
}

function save(key: string, ids: readonly number[] | null) {
  (ids?.length ? AsyncStorage.setItem(key, JSON.stringify(ids)) : AsyncStorage.removeItem(key)).catch(() => {});
}

export function saveCardOrder(ids: readonly number[] | null) {
  cardOrder.set(ids);
  save(ORDER_KEY, ids);
}

export function setCardHidden(id: number, hidden: boolean) {
  const rest = hiddenCards.get().filter((x) => x !== id);
  const next = hidden ? [...rest, id] : rest;
  hiddenCards.set(next);
  save(HIDDEN_KEY, next);
}

// «Як у банку»: the bank's order, every card shown
export function resetCards() {
  saveCardOrder(null);
  hiddenCards.set([]);
  save(HIDDEN_KEY, null);
}

async function load(key: string) {
  const saved = await AsyncStorage.getItem(key);
  if (!saved) return null;
  const parsed = Ids.safeParse(JSON.parse(saved));
  return parsed.success ? parsed.data : null;
}

// read once on start, next to the theme
export async function loadCardPrefs() {
  try {
    const [order, hidden, balance] = await Promise.all([
      load(ORDER_KEY),
      load(HIDDEN_KEY),
      AsyncStorage.getItem(BALANCE_HIDDEN_KEY),
    ]);
    if (order) cardOrder.set(order);
    if (hidden) hiddenCards.set(hidden);
    if (balance) balanceHidden.set(true);
  } catch {
    // nothing saved that can be read: the bank's order, all cards shown
  }
}
