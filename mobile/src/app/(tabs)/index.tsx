import { router } from 'expo-router';

import { Stub } from '@/ui/Stub';

export default function OverviewScreen() {
  return (
    <Stub
      background="none"
      title="Огляд"
      left={{ icon: 'person', label: 'Профіль', onPress: () => router.push('/profile') }}
      right={{ icon: 'bell', label: 'Сповіщення', dot: true }}
      note="Баланс · віджет карти · останні транзакції"
      links={[
        { label: 'Деталі транзакції (Сільпо)', href: '/transaction/silpo' },
        { label: 'Перевірки (dev)', href: '/dev/smoke' },
        { label: 'UI kit (dev)', href: '/dev/kit' },
      ]}
    />
  );
}
