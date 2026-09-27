import { Stub } from '@/ui/Stub';

export default function ProfileScreen() {
  return (
    <Stub
      background="accent"
      title="Профіль"
      note="Рахунки · правила категоризації · тема"
      links={[{ label: 'Назад на Огляд', href: '/' }]}
    />
  );
}
