import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme } from '@/theme';
import { Amount } from '@/ui/Amount';
import { Glass } from '@/ui/Glass';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Backdrop } from '@/ui/Backdrop';
import { ICONS } from '@/ui/icons/paths';
import { Text } from '@/ui/Text';

// dev screen: base UI pieces
const NAMES = Object.keys(ICONS) as IconName[];

export default function KitScreen() {
  const { c } = useTheme();

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: c.bg }]} edges={['bottom']}>
      <Backdrop variant="warm" />
      <ScrollView contentContainerStyle={styles.body}>
        <Text variant="screenTitle">Glass</Text>
        <Glass contentStyle={styles.card}>
          <Text variant="labelCaps" tone="ghost">Витрати за травень</Text>
          <Amount minor={1874000} variant="amountLg" cents={false} />
          <Text tone="muted">No blur, plain background</Text>
        </Glass>

        {/* busy backdrop to see the blur */}
        <View style={styles.backdrop}>
          <View style={[styles.spot, { backgroundColor: c.category.copper, left: -20, top: 10 }]} />
          <View style={[styles.spot, { backgroundColor: c.category.teal, right: -10, top: 60 }]} />
          <View style={[styles.spot, { backgroundColor: c.accent, left: 120, top: 120 }]} />
          <Glass blur radius={22} style={styles.overBackdrop} contentStyle={styles.card}>
            <Text variant="rowTitle">Blur on</Text>
            <Text tone="muted">Only for cards over the map</Text>
          </Glass>
        </View>

        <Text variant="screenTitle">Amounts</Text>
        <Amount minor={7254018} variant="amountXl" />
        <Amount minor={-52640} />
        <Amount minor={500000} sign="always" highlightIncome />
        <Amount minor={-500000} currency={985} locale="pl" />

        <Text variant="screenTitle">Icons · {NAMES.length}</Text>
        <View style={styles.grid}>
          {NAMES.map((name) => (
            <View key={name} style={styles.cell}>
              <Icon name={name} size={26} />
              <Text variant="rowCaption" tone="faint" numberOfLines={1}>{name}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  body: { padding: 20, gap: 14 },
  card: { padding: 16, gap: 6 },
  backdrop: { height: 220, justifyContent: 'center' },
  spot: { position: 'absolute', width: 120, height: 120, borderRadius: 60 },
  overBackdrop: { marginHorizontal: 10 },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  cell: { width: '25%', alignItems: 'center', gap: 6, paddingVertical: 10 },
});
