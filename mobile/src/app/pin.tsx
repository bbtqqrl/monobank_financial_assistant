import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { failure, success } from '@/lib/haptics';
import { checkPin, clearPin, lockEnabled, setPin } from '@/lib/security';
import { IconButton } from '@/ui/IconButton';
import { PinBackdrop } from '@/ui/PinBackdrop';
import { PinMark } from '@/ui/PinMark';
import { PinPad } from '@/ui/PinPad';

type Mode = 'new' | 'change' | 'off';
type Step = 'current' | 'create' | 'repeat';

// the param is only a wish: with a code set nothing skips asking for it first,
// and without one there's nothing to change or turn off
function pickMode(wish: string | undefined, hasCode: boolean): Mode {
  if (!hasCode) return 'new';
  return wish === 'off' ? 'off' : 'change';
}

const close = () => (router.canGoBack() ? router.back() : router.replace('/security'));

const TITLES: Record<Step, string> = {
  current: 'Поточний код',
  create: 'Придумай код',
  repeat: 'Повтори код',
};

// Full screen: setting the app's code (?mode=new), changing it (change) or turning it off
// (off): the current code first where there is one, a new one twice
export default function PinSheet() {
  const params = useLocalSearchParams<{ mode?: string }>();
  const [mode] = useState(() => pickMode(params.mode, lockEnabled.get()));
  const insets = useSafeAreaInsets();
  const [step, setStep] = useState<Step>(mode === 'new' ? 'create' : 'current');
  const [first, setFirst] = useState('');
  const [error, setError] = useState<string | null>(null);

  const wrong = (message: string) => {
    failure();
    setError(message);
    return false;
  };

  // false: the pad shows the code as wrong
  const complete = async (code: string) => {
    setError(null);
    if (step === 'current') {
      const result = await checkPin(code);
      if (result !== 'ok') return wrong(result === 'resting' ? 'Забагато спроб, зачекай трохи' : 'Неправильний код');
      if (mode === 'off') {
        await clearPin();
        success();
        close();
        return true;
      }
      setStep('create');
      return true;
    }
    if (step === 'create') {
      setFirst(code);
      setStep('repeat');
      return true;
    }
    if (code !== first) {
      setStep('create');
      return wrong('Коди не збіглися, спробуй ще');
    }
    await setPin(code);
    success();
    close();
    return true;
  };

  return (
    <View style={[styles.screen, { paddingBottom: Math.max(insets.bottom, 16) + 8 }]}>
      <PinBackdrop />
      <PinPad
        mark={<PinMark />}
        title={TITLES[step]}
        hint={step === 'create' ? '4 цифри, щоб відкривати застосунок' : undefined}
        error={error}
        onComplete={complete}
      />
      {/* last, so it stays on top of the pad */}
      <View style={[styles.close, { top: insets.top + 8 }]}>
        <IconButton icon="chevronLeft" label="Назад" weight={1.9} onPress={close} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 24 },
  close: { position: 'absolute', left: 20, zIndex: 1 },
});
