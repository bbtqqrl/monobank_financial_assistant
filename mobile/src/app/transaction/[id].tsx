import { router, useLocalSearchParams } from 'expo-router';

import { Stub } from '@/ui/Stub';

export default function TransactionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <Stub
      background="green"
      title="Деталі транзакції"
      small
      left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: () => router.back() }}
      right={{ icon: 'dots', label: 'Ще', weight: 2.4 }}
      note={`id: ${id}`}
    />
  );
}
