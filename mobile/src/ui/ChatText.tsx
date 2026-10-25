import { Fragment, memo, type ReactNode } from 'react';
import { Text as RNText, StyleSheet, View } from 'react-native';

import { FONT } from '@/lib/fonts';
import { useTheme, withAlpha } from '@/theme';
import { Text } from '@/ui/Text';

// The assistant writes short paragraphs, sometimes a list and **bold**
// (its prompt rules out tables and headings), so that's all that's drawn.
// Sums of money stand out on their own, so the numbers are what the eye finds.

const BULLET = /^\s*[-•*]\s+/;
const NUMBERED = /^\s*(\d+)[.)]\s+/;
// 12 480 ₴, −45,50 ₴, 50 PLN, 9,99 USD, and ranges like 445–450 ₴
const AMOUNT = /([−-]?\d[\d   ]*(?:[.,]\d+)?(?:\s?[–-]\s?\d[\d   ]*(?:[.,]\d+)?)?\s?(?:₴|грн|PLN|USD|EUR|zł|€|\$))/;

function withAmounts(text: string, key: string): ReactNode[] {
  // odd pieces are the amounts
  return text.split(AMOUNT).map((part, i) =>
    i % 2 ? (
      // spaces inside a sum don't break, so "69 704 ₴" stays on one line
      <RNText key={`${key}-${i}`} style={styles.amount}>
        {part.replace(/ /g, '\u00A0')}
      </RNText>
    ) : (
      <Fragment key={`${key}-${i}`}>{part}</Fragment>
    ),
  );
}

function Inline({ text }: { text: string }) {
  // odd pieces were between ** and **
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 ? (
          // plain RN text, so it keeps the size of the line around it
          <RNText key={i} style={styles.bold}>
            {part}
          </RNText>
        ) : (
          // a ** still waiting for its pair while the reply streams isn't shown
          withAmounts(part.replace(/\*\*/g, ''), String(i))
        ),
      )}
    </>
  );
}

// the pupil that rides at the end of a reply while it's being written
function Caret() {
  const { c } = useTheme();
  return <RNText style={[styles.caret, { color: c.accent }]}>{' ●'}</RNText>;
}

function Line({ line, caret }: { line: string; caret: boolean }) {
  const { c } = useTheme();
  const numbered = line.match(NUMBERED);
  const bullet = !numbered && BULLET.test(line);
  if (!numbered && !bullet) {
    return (
      <Text style={styles.text} selectable>
        <Inline text={line} />
        {caret ? <Caret /> : null}
      </Text>
    );
  }
  return (
    <View style={styles.item}>
      {numbered ? (
        <Text style={[styles.text, styles.number]}>{`${numbered[1]}.`}</Text>
      ) : (
        <View style={styles.dotBox}>
          <View style={[styles.dot, { backgroundColor: withAlpha(c.ink, 0.5) }]} />
        </View>
      )}
      <Text style={[styles.text, styles.itemText]} selectable>
        <Inline text={line.replace(numbered ? NUMBERED : BULLET, '')} />
        {caret ? <Caret /> : null}
      </Text>
    </View>
  );
}

// a finished paragraph doesn't change, so it isn't redrawn as the reply grows
const Paragraph = memo(function Paragraph({ text, caret }: { text: string; caret: boolean }) {
  const lines = text.split('\n');
  return (
    <View style={styles.paragraph}>
      {lines.map((line, j) => (
        <Line key={j} line={line} caret={caret && j === lines.length - 1} />
      ))}
    </View>
  );
});

// caret: the reply is still being written
export function ChatText({ text, caret = false }: { text: string; caret?: boolean }) {
  const paragraphs = text
    .trim()
    .split(/\n{2,}/)
    .filter((p) => p.trim());
  return (
    <View style={styles.column}>
      {paragraphs.map((paragraph, i) => (
        <Paragraph key={i} text={paragraph} caret={caret && i === paragraphs.length - 1} />
      ))}
    </View>
  );
}

const LINE = 21;

const styles = StyleSheet.create({
  column: { gap: 10 },
  paragraph: { gap: 4 },
  // chat reads longer than a card caption, so a step up from body
  text: { fontFamily: FONT.ui.medium, fontSize: 15, lineHeight: LINE },
  bold: { fontFamily: FONT.ui.semiBold },
  amount: { fontFamily: FONT.ui.bold, fontVariant: ['tabular-nums'] },
  item: { flexDirection: 'row', gap: 8 },
  number: { minWidth: 16, fontVariant: ['tabular-nums'] },
  dotBox: { width: 16, height: LINE, alignItems: 'center', justifyContent: 'center' },
  dot: { width: 5, height: 5, borderRadius: 2.5 },
  itemText: { flex: 1 },
  caret: { fontSize: 11 },
});
