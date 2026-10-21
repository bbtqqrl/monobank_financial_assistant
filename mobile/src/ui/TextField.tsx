import type { ReactNode, Ref } from 'react';
import { StyleSheet, TextInput, type TextInputProps } from 'react-native';

import { FONT } from '@/lib/fonts';
import { useTheme } from '@/theme';
import { Glass } from '@/ui/Glass';

// Glass input, same shape as the search field in the design.
type Props = TextInputProps & {
  ref?: Ref<TextInput>;
  // a small button at the right end, like the password's eye
  trailing?: ReactNode;
};

export function TextField({ style, trailing, ...props }: Props) {
  const { c } = useTheme();

  return (
    <Glass radius={15} contentStyle={styles.box}>
      <TextInput
        placeholderTextColor={c.ghost}
        selectionColor={c.accent}
        maxFontSizeMultiplier={1.3}
        {...props}
        style={[styles.input, { color: c.ink }, style]}
      />
      {trailing}
    </Glass>
  );
}

const styles = StyleSheet.create({
  box: { height: 50, flexDirection: 'row', alignItems: 'center' },
  input: { flex: 1, height: '100%', paddingHorizontal: 14, fontFamily: FONT.ui.medium, fontSize: 15 },
});
