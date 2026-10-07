const rules = new Intl.PluralRules('uk');

// plural(3, ['транзакція', 'транзакції', 'транзакцій']) → "3 транзакції"
export function plural(n: number, [one, few, many]: [string, string, string]) {
  const form = rules.select(n);
  return `${n} ${form === 'one' ? one : form === 'many' ? many : few}`;
}
