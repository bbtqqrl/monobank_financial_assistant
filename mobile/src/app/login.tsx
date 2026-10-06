import { useRef, useState } from 'react';
import { KeyboardAvoidingView, Pressable, ScrollView, StyleSheet, View, type TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { register, signIn } from '@/api/auth';
import { ApiError } from '@/api/client';
import { FONT } from '@/lib/fonts';
import { Backdrop } from '@/ui/Backdrop';
import { Button } from '@/ui/Button';
import { Text } from '@/ui/Text';
import { TextField } from '@/ui/TextField';

type Mode = 'login' | 'register';

function describe(e: unknown, mode: Mode) {
  if (e instanceof ApiError) {
    if (e.status === 401) return 'Неправильна пошта або пароль';
    if (e.status === 409) return 'Акаунт з цією поштою вже є';
    if (e.status === 422) return mode === 'register' ? 'Перевір пошту, пароль від 8 символів' : 'Перевір пошту';
    return `Сервер відповів помилкою (${e.status})`;
  }
  return 'Немає зʼєднання з сервером';
}

// TODO: first draft, no design for onboarding yet
export default function LoginScreen() {
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const passwordRef = useRef<TextInput>(null);

  const submit = async () => {
    if (busy || !email.trim() || !password) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === 'login') await signIn(email.trim(), password);
      else await register(email.trim(), password);
      // the root layout switches to the tabs once tokens are saved
    } catch (e) {
      setError(describe(e, mode));
      setBusy(false);
    }
  };

  return (
    <View style={styles.screen}>
      <Backdrop variant="warm" />
      <KeyboardAvoidingView behavior="padding" style={styles.screen}>
        <SafeAreaView style={styles.screen}>
          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            <View style={styles.titles}>
              <Text style={styles.title}>{mode === 'login' ? 'Вхід' : 'Новий акаунт'}</Text>
              <Text tone="faint">Твої витрати з monobank в одному місці</Text>
            </View>

            <View style={styles.fields}>
              <TextField
                value={email}
                onChangeText={setEmail}
                placeholder="Пошта"
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="email"
                keyboardType="email-address"
                textContentType="username"
                returnKeyType="next"
                onSubmitEditing={() => passwordRef.current?.focus()}
              />
              <TextField
                ref={passwordRef}
                value={password}
                onChangeText={setPassword}
                placeholder="Пароль"
                secureTextEntry
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                textContentType={mode === 'login' ? 'password' : 'newPassword'}
                returnKeyType="go"
                onSubmitEditing={submit}
              />
            </View>

            {error ? <Text tone="danger">{error}</Text> : null}

            <Button
              label={mode === 'login' ? 'Увійти' : 'Створити акаунт'}
              onPress={submit}
              loading={busy}
              disabled={!email.trim() || !password}
            />
            <Pressable
              accessibilityRole="button"
              hitSlop={8}
              onPress={() => {
                setMode(mode === 'login' ? 'register' : 'login');
                setError(null);
              }}
            >
              <Text variant="link" tone="accentText" style={styles.switch}>
                {mode === 'login' ? 'Ще немає акаунта? Створити' : 'Вже є акаунт? Увійти'}
              </Text>
            </Pressable>
          </ScrollView>
        </SafeAreaView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  body: { flexGrow: 1, justifyContent: 'center', padding: 20, gap: 16 },
  titles: { gap: 6, marginBottom: 8 },
  title: { fontFamily: FONT.display.medium, fontSize: 28, lineHeight: 34, letterSpacing: -0.28 },
  fields: { gap: 10 },
  switch: { textAlign: 'center', paddingVertical: 6 },
});
