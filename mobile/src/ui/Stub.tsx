import { Link, type Href } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { FONT } from '@/lib/fonts';
import { TEXT, useTheme } from '@/theme';
import { Backdrop, type BackdropVariant } from '@/ui/Backdrop';
import { Text } from '@/ui/Text';

type Props = {
  title: string;
  note?: string;
  links?: { label: string; href: Href }[];
  // shared: transparent, the tabs layout draws the backdrop
  background?: BackdropVariant | 'shared';
};

// TODO: placeholder, remove once real screens are in
export function Stub({ title, note, links = [], background = 'shared' }: Props) {
  const { c } = useTheme();

  return (
    <View style={styles.screen}>
      {background !== 'shared' ? <Backdrop variant={background} /> : null}
      <SafeAreaView style={styles.screen}>
        <View style={styles.body}>
          <Text style={styles.title}>{title}</Text>
          {note ? <Text tone="faint">{note}</Text> : null}
          {links.map((l) => (
            <Link key={l.label} href={l.href} style={[TEXT.bodyStrong, styles.link, { color: c.accentText }]}>
              {l.label} →
            </Link>
          ))}
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  body: { flex: 1, padding: 20, gap: 10, justifyContent: 'center' },
  title: { fontFamily: FONT.display.medium, fontSize: 26, lineHeight: 32, letterSpacing: -0.26 },
  link: { paddingVertical: 6 },
});
