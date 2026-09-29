import { Stub } from '@/ui/Stub';

export default function BudgetsScreen() {
  return (
    <Stub
      background="green"
      title="Бюджети"
      left={{ icon: 'filter', label: 'Фільтр' }}
      right={{ icon: 'plus', label: 'Новий бюджет', weight: 2.2 }}
      note="Залишок до кінця місяця · ліміти за категоріями"
    />
  );
}
