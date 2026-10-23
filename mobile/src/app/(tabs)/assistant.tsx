import MaskedView from '@react-native-masked-view/masked-view';
import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, FlatList, ScrollView, StyleSheet, View } from 'react-native';
import { useReanimatedKeyboardAnimation } from 'react-native-keyboard-controller';
import Animated, { FadeIn, useAnimatedStyle, useSharedValue } from 'react-native-reanimated';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import type { ChatMessage } from '@/api/assistant';
import { hold } from '@/lib/haptics';
import { stepsOf, useAssistantChat, type PendingReply } from '@/lib/useAssistantChat';
import { Backdrop } from '@/ui/Backdrop';
import { Button } from '@/ui/Button';
import { ChatComposer } from '@/ui/ChatComposer';
import { AssistantAnswer, PendingAnswer, UserBubble } from '@/ui/ChatMessage';
import { ChatSuggestions, followUpsFor, FollowUps } from '@/ui/ChatSuggestions';
import { Header } from '@/ui/Header';
import { Confirm } from '@/ui/Confirm';
import { Text } from '@/ui/Text';

// between the field and whatever is under it: the tab bar or the keyboard
const COMPOSER_GAP = 8;
// a question and its answer sit closer than one exchange and the next
const IN_TURN = 14;
const BETWEEN_TURNS = 24;
// how far the messages fade out under the header and above the field
const FADE_TOP = 28;
const FADE_BOTTOM = 12;
const ENTER = FadeIn.duration(220);
// the header row: its glass buttons are 44 tall
const HEADER_H = 44;

type Row =
  | { key: string; kind: 'user'; text: string }
  | { key: string; kind: 'assistant'; id: number; text: string }
  | { key: string; kind: 'pending'; reply: PendingReply };

// newest first, for a list that grows upwards from the field
function rowsOf(messages: ChatMessage[], pending: PendingReply | null): Row[] {
  const rows: Row[] = [];
  if (pending) {
    rows.push({ key: 'pending', kind: 'pending', reply: pending });
    if (pending.question) rows.push({ key: 'question', kind: 'user', text: pending.question });
  }
  for (const m of [...messages].reverse()) {
    rows.push(
      m.role === 'user'
        ? { key: String(m.id), kind: 'user', text: m.text }
        : { key: String(m.id), kind: 'assistant', id: m.id, text: m.text },
    );
  }
  return rows;
}

// in a list drawn upside down the leading row is the one below
const Gap = ({ leadingItem }: { leadingItem?: Row }) => (
  <View style={{ height: leadingItem?.kind === 'user' ? BETWEEN_TURNS : IN_TURN }} />
);

// Messages fade out at the top under the header and at the bottom over the
// field instead of being cut off
function FadeEdges() {
  return (
    <View style={styles.fill}>
      <View
        style={[styles.fadeTop, { experimental_backgroundImage: 'linear-gradient(to bottom, rgba(0,0,0,0), #000)' }]}
      />
      <View style={[styles.fill, styles.solid]} />
      <View
        style={[styles.fadeBottom, { experimental_backgroundImage: 'linear-gradient(to top, rgba(0,0,0,0), #000)' }]}
      />
    </View>
  );
}

// Chat with the AI about the user's money: the open conversation, a field
// over the tab bar that rides up with the keyboard, the reply as it's written.
export default function AssistantScreen() {
  const insets = useSafeAreaInsets();
  const chat = useAssistantChat();
  const [typing, setTyping] = useState(false);
  const [asking, setAsking] = useState(false);
  const rows = rowsOf(chat.messages, chat.pending);
  const followUps =
    !chat.pending && !typing && chat.lastTools.length > 0
      ? followUpsFor(chat.lastTools, chat.messages.findLast((m) => m.role === 'user')?.text)
      : [];

  // how much of the bottom the tab bar takes; the keyboard covers it when up
  const tabBar = useSharedValue(insets.bottom);
  const keyboard = useReanimatedKeyboardAnimation();
  const lift = useAnimatedStyle(() => ({
    paddingBottom: Math.max(Math.abs(keyboard.height.get()), tabBar.get()) + COMPOSER_GAP,
  }));

  const renderRow = ({ item }: { item: Row }) => {
    if (item.kind === 'assistant') return <AssistantAnswer text={item.text} steps={stepsOf(item.id)} />;
    // only what's new in this session comes in softly; the history is just there
    return (
      <Animated.View entering={ENTER}>
        {item.kind === 'pending' ? (
          <PendingAnswer reply={item.reply} onRetry={chat.send} />
        ) : (
          <UserBubble text={item.text} />
        )}
      </Animated.View>
    );
  };

  const body = chat.loading ? (
    <ActivityIndicator style={styles.fill} />
  ) : chat.failed ? (
    <View style={[styles.fill, styles.message]}>
      <Text tone="danger">Не вдалося завантажити розмову</Text>
      <Button kind="secondary" label="Спробувати ще" onPress={chat.reload} />
    </View>
  ) : rows.length === 0 ? (
    <ScrollView
      style={styles.fill}
      contentContainerStyle={styles.empty}
      keyboardDismissMode="interactive"
      keyboardShouldPersistTaps="handled"
    >
      <ChatSuggestions onPick={chat.send} chips={!typing} />
    </ScrollView>
  ) : (
    <MaskedView style={styles.fill} maskElement={<FadeEdges />}>
      <FlatList
        style={styles.fill}
        data={rows}
        inverted
        keyExtractor={(r) => r.key}
        renderItem={renderRow}
        ItemSeparatorComponent={Gap}
        // drawn upside down, so the header sits under the newest answer
        ListHeaderComponent={
          followUps.length ? (
            <View style={styles.followUps}>
              <FollowUps items={followUps} onPick={chat.send} />
            </View>
          ) : null
        }
        contentContainerStyle={styles.list}
        keyboardDismissMode="interactive"
        keyboardShouldPersistTaps="handled"
      />
    </MaskedView>
  );

  const empty = chat.messages.length === 0 && !chat.pending;

  // the button sits where a thumb rests, so a second tap confirms; the chat isn't lost either way
  const startNew = () => {
    hold();
    setAsking(true);
  };

  return (
    <View style={styles.screen}>
      <Backdrop variant="accent" shared />
      {/* inside a tab the bottom safe area includes the tab bar */}
      <SafeAreaView
        edges={['bottom']}
        pointerEvents="none"
        style={styles.probe}
        onLayout={(e) => tabBar.set(e.nativeEvent.layout.height)}
      />
      <View style={[styles.top, { paddingTop: insets.top + 11 }]}>
        <Header
          title="Асистент"
          left={{ icon: 'history', label: 'Розмови', onPress: () => router.push('/assistant-history') }}
          right={{ icon: 'compose', label: 'Нова розмова', onPress: startNew, disabled: empty || chat.busy }}
        />
      </View>
      <Animated.View style={[styles.fill, lift]}>
        {body}
        <View style={styles.composer}>
          <ChatComposer busy={chat.busy} onSend={chat.send} onStop={chat.stop} onTyping={setTyping} />
        </View>
      </Animated.View>
      {asking ? (
        <Confirm
          question="Почати нову розмову?"
          style={{ top: insets.top + 11 + HEADER_H + 8, right: 20 }}
          onYes={chat.startNew}
          onClose={() => setAsking(false)}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  fill: { flex: 1 },
  solid: { backgroundColor: '#000' },
  fadeTop: { height: FADE_TOP },
  fadeBottom: { height: FADE_BOTTOM },
  probe: { position: 'absolute', left: 0, right: 0, bottom: 0 },
  top: { paddingHorizontal: 20 },
  message: { gap: 12, alignItems: 'center', justifyContent: 'center' },
  empty: { flexGrow: 1, justifyContent: 'flex-end', paddingHorizontal: 20, paddingVertical: 16 },
  list: { paddingHorizontal: 20, paddingTop: 16, paddingBottom: FADE_TOP },
  followUps: { marginHorizontal: -20, paddingTop: IN_TURN },
  composer: { paddingHorizontal: 20 },
});
