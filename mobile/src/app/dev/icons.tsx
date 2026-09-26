import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme } from '@/theme';
import { Amount } from '@/ui/Amount';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { ICONS } from '@/ui/icons/paths';
import { Text } from '@/ui/Text';

// dev screen: all icons + amount samples
const NAMES = Object.keys(ICONS) as IconName[];

export default function IconsScreen() {
  const { c } = useTheme();

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: c.bg }]} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.body}>
        <Text variant="screenTitle">Icons · {NAMES.length}</Text>
        <View style={styles.grid}>
          {NAMES.map((name) => (
            <View key={name} style={styles.cell}>
              <Icon name={name} size={26} />
              <Text variant="rowCaption" tone="faint" numberOfLines={1}>{name}</Text>
            </View>
          ))}
        </View>

        <Text variant="screenTitle">Amounts</Text>
        <Amount minor={7254018} variant="amountXl" />
        <Amount minor={1874000} variant="amountLg" cents={false} />
        <Amount minor={-52640} />
        <Amount minor={500000} sign="always" highlightIncome />
        <Amount minor={-500000} currency={985} locale="pl" />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  body: { padding: 20, gap: 14 },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  cell: { width: '25%', alignItems: 'center', gap: 6, paddingVertical: 10 },
});
