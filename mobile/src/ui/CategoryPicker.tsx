import { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useCategories, type CategoryBrief, type CategoryKind, type CategoryNode } from '@/api/categories';
import { categoryLook, type CategoryLook } from '@/lib/categories';
import { Button } from '@/ui/Button';
import { CategoryOption } from '@/ui/CategoryOption';
import { SearchField } from '@/ui/SearchField';
import { SheetHeader } from '@/ui/SheetHeader';
import { Text } from '@/ui/Text';

type Props = {
  title: string;
  subtitle: string;
  // a line under the search, e.g. what else the choice changes
  note?: string;
  selectedId: number | null;
  // a first row that clears the choice
  allLabel?: string;
  // only these kinds can be picked, the rest are left out
  kinds?: readonly CategoryKind[];
  // the row being saved shows a spinner, the others wait
  busyId?: number;
  onPick: (category: CategoryBrief | null) => void;
  onClose: () => void;
};

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

// Searchable category tree for a sheet. The iOS sheet sizes its scroll view
// itself and expects exactly two children: a header that keeps its own native
// view, and the list.
export function CategoryPicker({ title, subtitle, note, selectedId, allLabel, kinds, busyId, onPick, onClose }: Props) {
  const insets = useSafeAreaInsets();
  const categories = useCategories();
  const [query, setQuery] = useState('');
  // parents opened or closed by hand; the one holding the pick starts open,
  // also when the categories arrive after the sheet
  const [toggled, setToggled] = useState<ReadonlySet<number>>(() => new Set());
  const pickParent = categories.data?.find((p) => p.children.some((ch) => ch.id === selectedId))?.id;
  const isOpen = (id: number) => (id === pickParent) !== toggled.has(id);

  const toggle = (id: number) =>
    setToggled((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const rows: RowProps = {
    selectedId,
    busyId,
    onPick: (category) => {
      if (busyId === undefined) onPick(brief(category));
    },
  };
  const q = normalize(query);
  const tree = categories.data?.filter((p) => !kinds || kinds.includes(p.kind)) ?? [];

  return (
    <>
      <View collapsable={false} style={styles.top}>
        <SheetHeader title={title} subtitle={subtitle} onClose={onClose} />
        <View style={styles.search}>
          <SearchField value={query} onChangeText={setQuery} placeholder="Пошук категорії" returnKeyType="done" />
        </View>
        {note ? (
          <Text variant="rowCaption" tone="muted" style={styles.note}>
            {note}
          </Text>
        ) : null}
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
          <Found tree={tree} query={q} {...rows} />
        ) : (
          <>
            {allLabel ? (
              <CategoryOption
                look={ALL_LOOK}
                name={allLabel}
                selected={selectedId === null}
                onPress={() => onPick(null)}
              />
            ) : null}
            {SECTIONS.map(({ kind, title: sectionTitle }) => {
              const roots = tree.filter((p) => p.kind === kind);
              if (roots.length === 0) return null;
              return (
                <View key={kind} style={styles.section}>
                  <Text variant="labelCaps" tone="ghost" style={styles.sectionTitle}>
                    {sectionTitle}
                  </Text>
                  {roots.map((p) => (
                    <Branch key={p.id} node={p} expanded={isOpen(p.id)} onToggle={() => toggle(p.id)} {...rows} />
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

type RowProps = { selectedId: number | null; busyId?: number; onPick: (c: CategoryBrief) => void };

function Option({ category, selectedId, busyId, onPick, ...rest }: RowProps & {
  category: CategoryBrief;
  caption?: string;
  nested?: boolean;
  expanded?: boolean;
  onToggle?: () => void;
}) {
  return (
    <CategoryOption
      look={look(category)}
      name={category.name}
      selected={selectedId === category.id}
      busy={busyId === category.id}
      onPress={() => onPick(category)}
      {...rest}
    />
  );
}

function Branch({ node, expanded, onToggle, ...rows }: RowProps & {
  node: CategoryNode;
  expanded: boolean;
  onToggle: () => void;
}) {
  const hasChildren = node.children.length > 0;
  return (
    <>
      <Option category={node} expanded={expanded} onToggle={hasChildren ? onToggle : undefined} {...rows} />
      {hasChildren && expanded ? node.children.map((ch) => <Option key={ch.id} category={ch} nested {...rows} />) : null}
    </>
  );
}

// search results: one flat list, a child shows its parent under the name
function Found({ tree, query, ...rows }: RowProps & { tree: CategoryNode[]; query: string }) {
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
    <Option key={category.id} category={category} caption={parent} {...rows} />
  ));
}

const styles = StyleSheet.create({
  top: { paddingTop: 22, paddingHorizontal: 20, paddingBottom: 10, gap: 14 },
  search: { flexDirection: 'row' },
  note: { marginTop: -4, paddingHorizontal: 4, fontSize: 12 },
  content: { paddingHorizontal: 14, gap: 2 },
  section: { gap: 2, marginTop: 10 },
  sectionTitle: { paddingHorizontal: 6, paddingBottom: 4 },
  message: { marginTop: 32, gap: 14, paddingHorizontal: 6 },
  center: { textAlign: 'center' },
});
