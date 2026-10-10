import { StyleSheet, View } from 'react-native';

import { Text } from '@/ui/Text';

type Props = {
  title: string;
  subtitle?: string;
};

// Title and a line under it, centred. No close button: sheets close with a swipe.
export function SheetHeader({ title, subtitle }: Props) {
  return (
    <View style={styles.head}>
      <Text variant="screenTitle" style={styles.center}>
        {title}
      </Text>
      {subtitle ? (
        <Text variant="rowCaption" tone="faint" style={[styles.subtitle, styles.center]} numberOfLines={2}>
          {subtitle}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  head: { gap: 3, alignItems: 'center' },
  center: { textAlign: 'center' },
  subtitle: { fontSize: 12.5 },
});
