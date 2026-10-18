import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';
import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import { z } from 'zod';

import { getTokens, subscribeTokens } from '@/api/tokens';
import { createStore } from '@/lib/store';

export type LockAfter = 'now' | '1m' | '5m';

// how long the app may sit in the background before it asks again
export const LOCK_DELAY_MS: Record<LockAfter, number> = { now: 0, '1m': 60_000, '5m': 5 * 60_000 };

export const PIN_LENGTH = 4;
// wrong codes in a row before the pad rests for a while
const MAX_TRIES = 5;
// each rest is longer than the one before, until a right code
const REST_STEPS_MS = [30_000, 60_000, 5 * 60_000, 15 * 60_000];

const PREFS_KEY = 'security';
const PIN_KEY = 'pin';
const TRIES_KEY = 'pinTries';

const PrefsSchema = z.object({
  lock: z.boolean(),
  biometric: z.boolean().default(false),
  after: z.enum(['now', '1m', '5m']),
});
type Prefs = z.infer<typeof PrefsSchema>;

const PinSchema = z.object({ salt: z.string(), hash: z.string() });
// kept in the Keychain, so restarting the app doesn't give fresh tries
const TriesSchema = z.object({ wrong: z.number(), rests: z.number(), until: z.number() });
type Tries = z.infer<typeof TriesSchema>;
const NO_TRIES: Tries = { wrong: 0, rests: 0, until: 0 };

// a code is set: the app opens only after it (or Face ID)
export const lockEnabled = createStore(false);
// Face ID may open it instead of the code
export const biometricEnabled = createStore(false);
export const lockAfter = createStore<LockAfter>('now');
// the lock screen is up right now
export const locked = createStore(false);
// a Face ID prompt is up: it makes the app inactive, which shouldn't count as leaving
export const authenticating = createStore(false);
// after too many wrong codes the pad waits from..until (ms)
export type PinRest = { from: number; until: number };
export const pinRest = createStore<PinRest>({ from: 0, until: 0 });

let tries = NO_TRIES;

async function saveTries(next: Tries) {
  tries = next;
  if (next === NO_TRIES) await SecureStore.deleteItemAsync(TRIES_KEY).catch(() => {});
  else await SecureStore.setItemAsync(TRIES_KEY, JSON.stringify(next)).catch(() => {});
}

function save() {
  const prefs: Prefs = {
    lock: lockEnabled.get(),
    biometric: biometricEnabled.get(),
    after: lockAfter.get(),
  };
  AsyncStorage.setItem(PREFS_KEY, JSON.stringify(prefs)).catch(() => {});
}

export function setBiometricEnabled(on: boolean) {
  biometricEnabled.set(on);
  save();
}

export function setLockAfter(after: LockAfter) {
  lockAfter.set(after);
  save();
}

const digest = (salt: string, code: string) => Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, `${salt}:${code}`);

// only a salted hash is kept, in the Keychain
export async function setPin(code: string) {
  const salt = Crypto.randomUUID();
  await SecureStore.setItemAsync(PIN_KEY, JSON.stringify({ salt, hash: await digest(salt, code) }));
  lockEnabled.set(true);
  save();
}

export async function clearPin() {
  await SecureStore.deleteItemAsync(PIN_KEY).catch(() => {});
  await saveTries(NO_TRIES);
  pinRest.set({ from: 0, until: 0 });
  lockEnabled.set(false);
  biometricEnabled.set(false);
  locked.set(false);
  save();
}

// The code belongs to the account it was set in: signing out, by hand, on all
// devices or when the session runs out, takes it away
let hadTokens = !!getTokens();
subscribeTokens(() => {
  const now = getTokens();
  if (hadTokens && now === null) clearPin();
  hadTokens = !!now;
});

async function storedPin() {
  try {
    const raw = await SecureStore.getItemAsync(PIN_KEY);
    const parsed = raw ? PinSchema.safeParse(JSON.parse(raw)) : null;
    return parsed?.success ? parsed.data : null;
  } catch {
    return null;
  }
}

export type PinCheck = 'ok' | 'wrong' | 'resting';

// counts wrong tries; after MAX_TRIES the pad rests, longer every time.
// Saved before answering, so killing the app right after doesn't undo a try.
export async function checkPin(code: string): Promise<PinCheck> {
  if (Date.now() < tries.until) return 'resting';
  const pin = await storedPin();
  if (pin && (await digest(pin.salt, code)) === pin.hash) {
    await saveTries(NO_TRIES);
    return 'ok';
  }
  const wrong = tries.wrong + 1;
  if (wrong < MAX_TRIES) {
    await saveTries({ ...tries, wrong });
    return 'wrong';
  }
  const from = Date.now();
  const until = from + REST_STEPS_MS[Math.min(tries.rests, REST_STEPS_MS.length - 1)]!;
  await saveTries({ wrong: 0, rests: tries.rests + 1, until });
  pinRest.set({ from, until });
  return 'resting';
}

async function loadTries() {
  try {
    const raw = await SecureStore.getItemAsync(TRIES_KEY);
    const parsed = raw ? TriesSchema.safeParse(JSON.parse(raw)) : null;
    if (!parsed?.success) return;
    tries = parsed.data;
    const now = Date.now();
    if (tries.until > now) pinRest.set({ from: now, until: tries.until });
  } catch {
    // no saved tries: a clean start
  }
}

// read before the first screen: with a code set, the app starts locked, so
// nothing shows before it
export async function loadSecurityPrefs() {
  await loadTries();
  try {
    const raw = await AsyncStorage.getItem(PREFS_KEY);
    const prefs = raw ? PrefsSchema.safeParse(JSON.parse(raw)) : null;
    if (!prefs?.success) return;
    // a lock without a stored code could never open
    const lock = prefs.data.lock && (await storedPin()) !== null;
    lockEnabled.set(lock);
    biometricEnabled.set(lock && prefs.data.biometric);
    lockAfter.set(prefs.data.after);
    if (lock) locked.set(true);
  } catch {
    // keep the defaults: unlocked
  }
}

export type Biometry = {
  // Face ID or Touch ID is set up on the phone
  available: boolean;
  // "Face ID", "Touch ID", "відбиток пальця"
  name: string;
};

async function readBiometry(): Promise<Biometry> {
  const [enrolled, types] = await Promise.all([
    LocalAuthentication.isEnrolledAsync(),
    LocalAuthentication.supportedAuthenticationTypesAsync(),
  ]);
  const face = types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION);
  const name = Platform.OS === 'ios' ? (face ? 'Face ID' : 'Touch ID') : face ? 'обличчя' : 'відбиток пальця';
  return { available: enrolled && types.length > 0, name };
}

export function useBiometry(): Biometry | null {
  const [biometry, setBiometry] = useState<Biometry | null>(null);
  useEffect(() => {
    readBiometry()
      .then(setBiometry)
      .catch(() => setBiometry({ available: false, name: 'Face ID' }));
  }, []);
  return biometry;
}

// Face ID only: the app's own code is the fallback, not the phone's passcode
export async function authenticate(promptMessage: string): Promise<boolean> {
  authenticating.set(true);
  try {
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage,
      cancelLabel: 'Ввести код',
      disableDeviceFallback: true,
    });
    return result.success;
  } catch {
    return false;
  } finally {
    authenticating.set(false);
  }
}
