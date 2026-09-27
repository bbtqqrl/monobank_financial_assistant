import { Stub } from '@/ui/Stub';

export default function ProfileScreen() {
  return (
    <Stub
      title="Профіль"
      note="Рахунки · правила категоризації · тема"
      links={[{ label: 'Назад на Огляд', href: '/' }]}
    />
  );
}
