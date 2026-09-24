import { Stub } from '@/ui/Stub';

export default function OverviewScreen() {
  return (
    <Stub
      title="Огляд"
      note="Баланс · віджет карти · останні транзакції"
      links={[
        { label: 'Профіль', href: '/profile' },
        { label: 'Деталі транзакції (Сільпо)', href: '/transaction/silpo' },
        { label: 'Перевірка Intl (dev)', href: '/dev/smoke' },
      ]}
    />
  );
}
