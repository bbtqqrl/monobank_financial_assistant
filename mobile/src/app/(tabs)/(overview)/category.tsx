import { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useCategories, type CategoryBrief, type CategoryKind, type CategoryNode } from '@/api/categories';
import { categoryLook, type CategoryLook } from '@/lib/categories';
import { listCategory } from '@/lib/categoryFilter';
import { closeSheet } from '@/lib/nav';
import { Button } from '@/ui/Button';
import { CategoryOption } from '@/ui/CategoryOption';
import { SearchField } from '@/ui/SearchField';
import { SheetHeader } from '@/ui/SheetHeader';
import { Text } from '@/ui/Text';

const SECTIONS: { kind: CategoryKind; title: string }[] = [
  { kind: 'expense', title: 'Витрати' },
  { kind: 'income', title: 'Доходи' },
  { kind: 'transfer', title: 'Рух коштів' },
  { kind: 'unknown', title: 'Інше' },
];

const ALL_LOOK: CategoryLook = { icon: 'list', color: 'neutral' };

// apostrophes come in three spellings: кав'ярні, кав’ярні, кавʼярні
const normalize = (s: string) => s.toLocaleLowerCase('uk').replace(/[’ʼ`]/g, "'").trim();

const brief = ({ id, name, slug, kind }: CategoryBrief): CategoryBrief => ({ id, name, slug, kind });

const look = (c: CategoryBrief) => categoryLook(c.slug, c.kind === 'income' ? 1 : -1);

// Category sheet: narrows the transactions list to one category
export default function CategorySheet() {
  const insets = useSafeAreaInsets();
  const categories = useCategories();
  const selected = listCategory.useValue();
  const [query, setQuery] = useState('');
  // the parent of a picked child starts open, so the pick is in view
  const [open, setOpen] = useState<ReadonlySet<number>>(() => {
    const parent = categories.data?.find((p) => p.children.some((ch) => ch.id === selected?.id));
    return new Set(parent ? [parent.id] : []);
  });

  const pick = (category: CategoryBrief | null) => {
    listCategory.set(category && brief(category));
    closeSheet();
  };

  const toggle = (id: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const q = normalize(query);

  // The iOS sheet sizes its scroll view itself and expects exactly two
  // children: a header that keeps its own native view, and the list.
  return (
    <>
      <View collapsable={false} style={styles.top}>
        <SheetHeader
          title="Категорія"
          subtitle={selected ? `Зараз: ${selected.name}` : 'Показати транзакції однієї категорії'}
          onClose={closeSheet}
        />
        <View style={styles.search}>
          <SearchField
            value={query}
            onChangeText={setQuery}
            placeholder="Пошук категорії"
            returnKeyType="done"
          />
        </View>
      </View>

      <ScrollView
        contentContainerStyle={[styles.content, { paddingBottom: Math.max(insets.bottom, 16) }]}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
      >
        {categories.isPending ? (
          <ActivityIndicator style={styles.message} />
        ) : categories.isError ? (
          <View style={styles.message}>
            <Text tone="faint" style={styles.center}>
              Не вдалося завантажити категорії
            </Text>
            <Button kind="secondary" label="Спробувати ще" onPress={() => categories.refetch()} />
          </View>
        ) : q ? (
          <Found tree={categories.data} query={q} selected={selected} onPick={pick} />
        ) : (
          <>
            <CategoryOption look={ALL_LOOK} name="Усі категорії" selected={!selected} onPress={() => pick(null)} />
            {SECTIONS.map(({ kind, title }) => {
              const roots = categories.data.filter((p) => p.kind === kind);
              if (roots.length === 0) return null;
              return (
                <View key={kind} style={styles.section}>
                  <Text variant="labelCaps" tone="ghost" style={styles.sectionTitle}>
                    {title}
                  </Text>
                  {roots.map((p) => (
                    <Branch
                      key={p.id}
                      node={p}
                      expanded={open.has(p.id)}
                      onToggle={() => toggle(p.id)}
                      selected={selected}
                      onPick={pick}
                    />
                  ))}
                </View>
              );
            })}
          </>
        )}
      </ScrollView>
    </>
  );
}

type PickProps = { selected: CategoryBrief | null; onPick: (c: CategoryBrief) => void };

function Branch({ node, expanded, onToggle, selected, onPick }: PickProps & {
  node: CategoryNode;
  expanded: boolean;
  onToggle: () => void;
}) {
  const hasChildren = node.children.length > 0;
  return (
    <>
      <CategoryOption
        look={look(node)}
        name={node.name}
        selected={selected?.id === node.id}
        onPress={() => onPick(node)}
        expanded={expanded}
        onToggle={hasChildren ? onToggle : undefined}
      />
      {hasChildren && expanded
        ? node.children.map((ch) => (
            <CategoryOption
              key={ch.id}
              nested
              look={look(ch)}
              name={ch.name}
              selected={selected?.id === ch.id}
              onPress={() => onPick(ch)}
            />
          ))
        : null}
    </>
  );
}

// search results: one flat list, a child shows its parent under the name
function Found({ tree, query, selected, onPick }: PickProps & { tree: CategoryNode[]; query: string }) {
  const matches = tree.flatMap((p) => [
    ...(normalize(p.name).includes(query) ? [{ category: p, parent: undefined }] : []),
    ...p.children.filter((ch) => normalize(ch.name).includes(query)).map((ch) => ({ category: ch, parent: p.name })),
  ]);

  if (matches.length === 0) {
    return (
      <Text tone="faint" style={[styles.message, styles.center]}>
        Такої категорії немає
      </Text>
    );
  }

  return matches.map(({ category, parent }) => (
    <CategoryOption
      key={category.id}
      look={look(category)}
      name={category.name}
      caption={parent}
      selected={selected?.id === category.id}
      onPress={() => onPick(category)}
    />
  ));
}

const styles = StyleSheet.create({
  top: { paddingTop: 22, paddingHorizontal: 20, paddingBottom: 10, gap: 14 },
  search: { flexDirection: 'row' },
  content: { paddingHorizontal: 14, gap: 2 },
  section: { gap: 2, marginTop: 10 },
  sectionTitle: { paddingHorizontal: 6, paddingBottom: 4 },
  message: { marginTop: 32, gap: 14, paddingHorizontal: 6 },
  center: { textAlign: 'center' },
});
