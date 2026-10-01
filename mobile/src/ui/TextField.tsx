import type { Ref } from 'react';
import { StyleSheet, TextInput, type TextInputProps } from 'react-native';

import { FONT } from '@/lib/fonts';
import { useTheme } from '@/theme';
import { Glass } from '@/ui/Glass';

// Glass input, same shape as the search field in the design.
export function TextField({ style, ...props }: TextInputProps & { ref?: Ref<TextInput> }) {
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
    </Glass>
  );
}

const styles = StyleSheet.create({
  box: { height: 50, justifyContent: 'center' },
  input: { height: '100%', paddingHorizontal: 14, fontFamily: FONT.ui.medium, fontSize: 15 },
});
