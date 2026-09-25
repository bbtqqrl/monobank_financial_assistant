import { Link, type Href } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { FONT } from '@/lib/fonts';
import { TEXT, useTheme } from '@/theme';

type Props = {
  title: string;
  note?: string;
  links?: { label: string; href: Href }[];
};

// TODO: placeholder, remove once real screens are in
export function Stub({ title, note, links = [] }: Props) {
  const { c } = useTheme();

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: c.bg }]}>
      <View style={styles.body}>
        <Text style={[styles.title, { color: c.ink }]}>{title}</Text>
        {note ? <Text style={[TEXT.body, { color: c.faint }]}>{note}</Text> : null}
        {links.map((l) => (
          <Link key={l.label} href={l.href} style={[TEXT.bodyStrong, styles.link, { color: c.accentText }]}>
            {l.label} →
          </Link>
        ))}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  body: { flex: 1, padding: 20, gap: 10, justifyContent: 'center' },
  title: { fontFamily: FONT.display.medium, fontSize: 26, letterSpacing: -0.26 },
  link: { paddingVertical: 6 },
});
