import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';

import { FONT } from '@/lib/fonts';
import { tap } from '@/lib/haptics';
import { plural } from '@/lib/plural';
import type { PendingReply, Step } from '@/lib/useAssistantChat';
import { useSmoothText } from '@/lib/useSmoothText';
import { useTheme } from '@/theme';
import { ChatText } from '@/ui/ChatText';
import { Icon } from '@/ui/icons/Icon';
import { ShimmerText } from '@/ui/ShimmerText';
import { ThinkingDot } from '@/ui/ThinkingDot';
import { Text } from '@/ui/Text';

const LABEL_IN = FadeIn.duration(180);
const LABEL_OUT = FadeOut.duration(140);

export function UserBubble({ text }: { text: string }) {
  const { c } = useTheme();
  return (
    <View style={[styles.user, { backgroundColor: c.accentFill }]}>
      <Text style={[styles.userText, { color: c.onPrimary }]} selectable>
        {text}
      </Text>
    </View>
  );
}

// The steps behind an answer, folded into one line: a tick and how many;
// a tap lists them
function Steps({ steps }: { steps: Step[] }) {
  const { c } = useTheme();
  const [open, setOpen] = useState(false);
  const count = plural(steps.length, ['крок', 'кроки', 'кроків']);
  return (
    <View style={styles.steps}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        accessibilityLabel={`${count}, що зробив асистент`}
        hitSlop={8}
        onPress={() => {
          tap();
          setOpen((o) => !o);
        }}
        style={styles.stepsHead}
      >
        <Icon name="check" size={13} color={c.positive} weight={2.4} />
        <Text variant="rowCaption" tone="onBackdrop">
          {count}
        </Text>
        <View style={open && styles.flipped}>
          <Icon name="chevronDown" size={12} color={c.onBackdrop} weight={2} />
        </View>
      </Pressable>
      {open ? (
        <Animated.View entering={FadeIn.duration(200)} style={styles.stepList}>
          {steps.map((s, i) => (
            <View key={i} style={styles.step}>
              <Icon name="check" size={12} color={c.positive} weight={2.4} />
              <Text variant="rowCaption" tone="onBackdrop" style={styles.stepText}>
                {s.label}
              </Text>
            </View>
          ))}
        </Animated.View>
      ) : null}
    </View>
  );
}

// A finished answer: plain text on the backdrop, like a page, not a card
export function AssistantAnswer({ text, steps }: { text: string; steps?: Step[] }) {
  return (
    <View style={styles.answer}>
      {steps?.length ? <Steps steps={steps} /> : null}
      <ChatText text={text} />
    </View>
  );
}

// The answer as it comes in. Before the first words: a pulsing dot and
// the step it's on, shimmering. Then the steps fold into a line and the
// text flows in with the pupil at its end.
export function PendingAnswer({ reply, onRetry }: { reply: PendingReply; onRetry: (text: string) => void }) {
  const text = useSmoothText(reply.text);
  const { retry, error } = reply;
  const working = reply.busy && !text;
  const label = reply.steps.at(-1)?.label ?? 'Думаю';

  return (
    <View style={styles.answer}>
      {working ? (
        <View style={styles.working}>
          <ThinkingDot />
          <Animated.View key={label} entering={LABEL_IN} exiting={LABEL_OUT} style={styles.label}>
            <ShimmerText style={styles.labelText}>{label}</ShimmerText>
          </Animated.View>
        </View>
      ) : reply.steps.length ? (
        <Steps steps={reply.steps} />
      ) : null}
      {text ? <ChatText text={text} caret={reply.busy} /> : null}
      {reply.stopped ? (
        <Text variant="rowCaption" tone="onBackdrop">
          Зупинено
        </Text>
      ) : null}
      {error ? (
        <View style={styles.error}>
          <Text variant="body" tone="danger">
            {error}
          </Text>
          {retry ? (
            <Pressable accessibilityRole="button" hitSlop={10} onPress={() => onRetry(retry)}>
              <Text variant="link" tone="accentText">
                Спробувати ще
              </Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  user: {
    alignSelf: 'flex-end',
    maxWidth: '80%',
    borderRadius: 20,
    borderBottomRightRadius: 6,
    borderCurve: 'continuous',
    paddingVertical: 10,
    paddingHorizontal: 14,
  },
  userText: { fontFamily: FONT.ui.medium, fontSize: 15, lineHeight: 21 },
  answer: { gap: 10, paddingRight: 12 },
  working: { flexDirection: 'row', alignItems: 'center', gap: 9, minHeight: 22 },
  label: { flexShrink: 1 },
  labelText: { fontFamily: FONT.ui.semiBold, fontSize: 13.5, lineHeight: 18 },
  steps: { gap: 8 },
  stepsHead: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start' },
  flipped: { transform: [{ rotate: '180deg' }] },
  stepList: { gap: 6, paddingLeft: 2 },
  step: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  stepText: { flexShrink: 1 },
  error: { gap: 6 },
});
