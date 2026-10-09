import { listCategory } from '@/lib/categoryFilter';
import { closeSheet } from '@/lib/nav';
import { CategoryPicker } from '@/ui/CategoryPicker';

// Category sheet: narrows the transactions list to one category
export default function CategorySheet() {
  const selected = listCategory.useValue();

  return (
    <CategoryPicker
      title="Категорія"
      subtitle={selected ? `Зараз: ${selected.name}` : 'Показати транзакції однієї категорії'}
      selectedId={selected?.id ?? null}
      allLabel="Усі категорії"
      onPick={(category) => {
        listCategory.set(category);
        closeSheet();
      }}
      onClose={closeSheet}
    />
  );
}
