import { router, useLocalSearchParams } from 'expo-router';

import { DRAFT_KINDS, draftCategory } from '@/lib/draft';
import { CategoryPicker } from '@/ui/CategoryPicker';

const close = () => (router.canGoBack() ? router.back() : router.replace('/new'));

// Category for a new transaction, on top of its sheet
export default function DraftCategorySheet() {
  const { direction } = useLocalSearchParams<{ direction?: string }>();
  const income = direction === 'income';
  const selected = draftCategory.useValue();

  return (
    <CategoryPicker
      title="Категорія"
      subtitle={income ? 'Звідки ці гроші' : 'На що пішли гроші'}
      selectedId={selected?.id ?? null}
      kinds={DRAFT_KINDS[income ? 'income' : 'expense']}
      onPick={(category) => {
        draftCategory.set(category);
        close();
      }}
      onClose={close}
    />
  );
}
