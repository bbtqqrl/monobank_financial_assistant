import { Link, type Href } from 'expo-router';
import { StyleSheet, Text, View, useColorScheme } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { FONT } from '@/lib/fonts';

type Props = {
  title: string;
  note?: string;
  links?: { label: string; href: Href }[];
};

// TODO: placeholder, remove once real screens are in
export function Stub({ title, note, links = [] }: Props) {
  const dark = useColorScheme() === 'dark';
  const ink = dark ? '#F0EDE6' : '#1A1714';
  const faint = dark ? '#8A8690' : '#8C857C';

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: dark ? '#141318' : '#EFEDE8' }]}>
      <View style={styles.body}>
        <Text style={[styles.title, { color: ink }]}>{title}</Text>
        {note ? <Text style={[styles.note, { color: faint }]}>{note}</Text> : null}
        {links.map((l) => (
          <Link key={l.label} href={l.href} style={[styles.link, { color: '#3A50B4' }]}>
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
  note: { fontFamily: FONT.ui.medium, fontSize: 14, lineHeight: 19 },
  link: { fontFamily: FONT.ui.semiBold, fontSize: 15, paddingVertical: 6 },
});
