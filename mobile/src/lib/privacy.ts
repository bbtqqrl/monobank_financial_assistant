import { balanceHidden } from '@/lib/cardOrder';

export const MASK = '••••';

// While balances are hidden on the Overview every amount turns to dots, so
// nobody reads them over a shoulder on any screen
export function useMask() {
  const hidden = balanceHidden.useValue();
  return (text: string) => (hidden ? MASK : text);
}
