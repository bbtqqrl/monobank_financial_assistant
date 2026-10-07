import type { Ref } from 'react';
import { Pressable, StyleSheet, TextInput, type TextInputProps } from 'react-native';

import { FONT } from '@/lib/fonts';
import { useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Icon } from '@/ui/icons/Icon';

type Props = Omit<TextInputProps, 'style'> & {
  value: string;
  onChangeText: (text: string) => void;
  ref?: Ref<TextInput>;
};

export function SearchField({ value, onChangeText, ...props }: Props) {
  const { c } = useTheme();

  return (
    <Glass radius={15} style={styles.outer} contentStyle={styles.box}>
      <Icon name="search" size={18} color={c.ghost} weight={1.8} />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholderTextColor={c.ghost}
        selectionColor={c.accent}
        maxFontSizeMultiplier={1.3}
        returnKeyType="search"
        autoCorrect={false}
        clearButtonMode="never"
        {...props}
        style={[styles.input, { color: c.ink }]}
      />
      {value ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Очистити"
          hitSlop={10}
          onPress={() => onChangeText('')}
          style={[styles.clear, { backgroundColor: withAlpha(c.shade, 0.12) }]}
        >
          <Icon name="close" size={11} color={c.inkSoft} weight={2.4} />
        </Pressable>
      ) : null}
    </Glass>
  );
}

const styles = StyleSheet.create({
  outer: { flex: 1 },
  // Figma: 46 high, 0 14 0 12
  box: { height: 46, flexDirection: 'row', alignItems: 'center', gap: 8, paddingLeft: 12, paddingRight: 12 },
  input: { flex: 1, height: '100%', fontFamily: FONT.ui.medium, fontSize: 15 },
  clear: { width: 18, height: 18, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
});
