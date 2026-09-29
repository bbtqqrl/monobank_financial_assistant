import { Link, type Href } from 'expo-router';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { TEXT, useTheme } from '@/theme';
import { Backdrop, type BackdropVariant } from '@/ui/Backdrop';
import { Header } from '@/ui/Header';
import { Text } from '@/ui/Text';

type Props = ComponentProps<typeof Header> & {
  note?: string;
  links?: { label: string; href: Href }[];
  background?: BackdropVariant;
};

// TODO: placeholder, remove once real screens are in
export function Stub({ note, links = [], background = 'warm', ...header }: Props) {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.screen}>
      <Backdrop variant={background} />
      {/* Figma: header at 58 under a 47pt status bar */}
      <View style={[styles.top, { paddingTop: insets.top + 11 }]}>
        <Header {...header} />
      </View>
      <View style={styles.body}>
        {note ? <Text tone="faint">{note}</Text> : null}
        {links.map((l) => (
          <Link key={l.label} href={l.href} style={[TEXT.bodyStrong, styles.link, { color: c.accentText }]}>
            {l.label} →
          </Link>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  top: { paddingHorizontal: 20 },
  body: { flex: 1, padding: 20, gap: 10, justifyContent: 'center' },
  link: { paddingVertical: 6 },
});
