import { router } from 'expo-router';

import { budgetCategory } from '@/lib/draft';
import { CategoryPicker } from '@/ui/CategoryPicker';

const close = () => (router.canGoBack() ? router.back() : router.replace('/budget'));

// Category for a new budget, on top of its sheet: spending ones only
export default function BudgetCategorySheet() {
  const selected = budgetCategory.useValue();

  return (
    <CategoryPicker
      title="Категорія"
      subtitle="На що ставимо ліміт"
      selectedId={selected?.id ?? null}
      kinds={['expense']}
      onPick={(category) => {
        budgetCategory.set(category);
        close();
      }}
    />
  );
}
