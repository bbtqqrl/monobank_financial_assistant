import { router } from 'expo-router';
import { useState } from 'react';

import { signOut } from '@/api/auth';
import { Button } from '@/ui/Button';
import { Header } from '@/ui/Header';
import { Screen } from '@/ui/Screen';

export default function ProfileScreen() {
  const [busy, setBusy] = useState(false);

  return (
    <Screen background="accent">
      <Header
        title="Профіль"
        left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: () => router.back() }}
        right={{ icon: 'gear', label: 'Налаштування' }}
      />
      <Button
        kind="secondary"
        label="Вийти з акаунта"
        loading={busy}
        onPress={() => {
          setBusy(true);
          signOut();
        }}
      />
    </Screen>
  );
}
