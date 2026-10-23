import AsyncStorage from '@react-native-async-storage/async-storage';
import { z } from 'zod';

import { createStore } from '@/lib/store';

// Names the user gave to chats with the assistant, by chat id. Kept on the
// phone until the backend can rename a chat itself.
const KEY = 'chatTitles';
const MAX_LENGTH = 60;

const Titles = z.record(z.string(), z.string());

export const chatTitles = createStore<Readonly<Record<string, string>>>({});

// an empty name brings back the one the chat had
export function setChatTitle(id: number, title: string) {
  const name = title.trim().slice(0, MAX_LENGTH);
  const { [id]: _old, ...rest } = chatTitles.get();
  const next = name ? { ...rest, [id]: name } : rest;
  chatTitles.set(next);
  AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => {});
}

export function forgetChatTitle(id: number) {
  if (!(id in chatTitles.get())) return;
  setChatTitle(id, '');
}

// read once on start, next to the theme
export async function loadChatTitles() {
  try {
    const saved = await AsyncStorage.getItem(KEY);
    const parsed = saved ? Titles.safeParse(JSON.parse(saved)) : null;
    if (parsed?.success) chatTitles.set(parsed.data);
  } catch {
    // unreadable, start without names
  }
}
