import { Stub } from '@/ui/Stub';

export default function AnalyticsScreen() {
  return (
    <Stub
      title="Аналітика"
      left={{ icon: 'filter', label: 'Фільтр' }}
      right={{ icon: 'share', label: 'Поділитися' }}
      note="Підсумок · Категорії · Тренди"
    />
  );
}
