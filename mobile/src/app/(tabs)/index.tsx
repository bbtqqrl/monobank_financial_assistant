import { Stub } from '@/ui/Stub';

export default function OverviewScreen() {
  return (
    <Stub
      title="Огляд"
      note="Баланс · віджет карти · останні транзакції"
      links={[
        { label: 'Профіль', href: '/profile' },
        { label: 'Деталі транзакції (Сільпо)', href: '/transaction/silpo' },
        { label: 'Перевірки (dev)', href: '/dev/smoke' },
        { label: 'Іконки й суми (dev)', href: '/dev/icons' },
      ]}
    />
  );
}
