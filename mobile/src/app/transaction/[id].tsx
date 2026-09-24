import { useLocalSearchParams } from 'expo-router';

import { Stub } from '@/ui/Stub';

export default function TransactionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <Stub
      title="Деталі транзакції"
      note={`id: ${id}`}
      links={[{ label: 'Назад на Огляд', href: '/' }]}
    />
  );
}
