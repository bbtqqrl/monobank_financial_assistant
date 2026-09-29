import { router } from 'expo-router';

import { Stub } from '@/ui/Stub';

export default function ProfileScreen() {
  return (
    <Stub
      background="accent"
      title="Профіль"
      left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: () => router.back() }}
      right={{ icon: 'gear', label: 'Налаштування' }}
      note="Рахунки · правила категоризації · тема"
    />
  );
}
