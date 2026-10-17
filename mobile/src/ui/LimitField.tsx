import type { RefObject } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';

import { FONT } from '@/lib/fonts';
import { useTheme } from '@/theme';
import { AmountDigits } from '@/ui/AmountDigits';
import { Text } from '@/ui/Text';

type Props = {
  text: string;
  onText: (text: string) => void;
  inputRef?: RefObject<TextInput | null>;
};

// whole hryvnias, up to 9 999 999
const LIMIT_TYPING = /^\d{0,7}$/;

// A budget's limit typed in place: big digits that animate, an invisible
// input on top takes the typing
export function LimitField({ text, onText, inputRef }: Props) {
  const { c } = useTheme();

  return (
    <View style={styles.row}>
      <AmountDigits
        text={text}
        style={[styles.digits, { color: c.ink }]}
        placeholderStyle={[styles.digits, { color: c.ghost }]}
      />
      <Text style={[styles.digits, { color: c.ghost }]}>₴</Text>
      <TextInput
        ref={inputRef}
        value={text}
        onChangeText={(next) => {
          if (LIMIT_TYPING.test(next)) onText(next);
        }}
        keyboardType="number-pad"
        caretHidden
        contextMenuHidden
        accessibilityLabel="Ліміт у гривнях"
        style={[StyleSheet.absoluteFill, styles.hidden]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  digits: { fontFamily: FONT.ui.bold, fontSize: 40, lineHeight: 48, letterSpacing: -0.5 },
  hidden: { color: 'transparent' },
});
