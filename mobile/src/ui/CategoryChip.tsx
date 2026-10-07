import { StyleSheet, View } from 'react-native';

import type { CategoryLook } from '@/lib/categories';
import { useTheme, withAlpha } from '@/theme';
import { Icon } from '@/ui/icons/Icon';

type Props = CategoryLook & {
  size?: number;
  // Figma: 40 / r14 in lists, 38 / r13 on Overview, 36 / r12 and 62 / r22 on details
  radius?: number;
};

// Tinted tile with the category icon
export function CategoryChip({ icon, color, size = 40, radius }: Props) {
  const { c } = useTheme();
  const tone = c.category[color];

  return (
    <View
      style={[
        styles.chip,
        {
          width: size,
          height: size,
          borderRadius: radius ?? (size <= 38 ? 13 : 14),
          backgroundColor: withAlpha(tone, 0.14),
        },
      ]}
    >
      <Icon name={icon} size={Math.round(size * 0.5)} color={tone} />
    </View>
  );
}

const styles = StyleSheet.create({
  chip: { alignItems: 'center', justifyContent: 'center' },
});
