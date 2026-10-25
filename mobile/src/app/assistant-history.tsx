import { useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import Animated, { FadeIn, FadeOut, LinearTransition } from 'react-native-reanimated';

import { CONVERSATIONS_KEY, deleteConversation, useConversations, type Conversation } from '@/api/assistant';
import { chatTitles, forgetChatTitle, setChatTitle } from '@/lib/chatTitles';
import { whenLabel } from '@/lib/time';
import { openChat } from '@/lib/useAssistantChat';
import { useTheme, withAlpha } from '@/theme';
import { ChatHistoryRow } from '@/ui/ChatHistoryRow';
import { SheetHeader } from '@/ui/SheetHeader';
import { Text } from '@/ui/Text';

const seconds = (iso: string) => new Date(iso).getTime() / 1000;
const LIST_MOVE = LinearTransition.duration(220);
const FAILED_MS = 3000;

// Past chats with the assistant, newest first
export default function AssistantHistorySheet() {
  const { c } = useTheme();
  const qc = useQueryClient();
  const conversations = useConversations();
  const picked = openChat.useValue();
  const names = chatTitles.useValue();
  const items = conversations.data ?? [];
  const current = picked === undefined ? items[0]?.id : picked;
  // a delete the server refused, said under the title for a moment
  const [failed, setFailed] = useState(false);

  const open = (id: number) => {
    openChat.set(id);
    router.back();
  };

  // gone from the list at once; back if the server says no
  const remove = async (id: number) => {
    const before = qc.getQueryData<Conversation[]>(CONVERSATIONS_KEY);
    qc.setQueryData<Conversation[]>(CONVERSATIONS_KEY, (list) => list?.filter((x) => x.id !== id));
    try {
      await deleteConversation(id);
      forgetChatTitle(id);
      if (id === current) openChat.set(undefined);
    } catch {
      qc.setQueryData(CONVERSATIONS_KEY, before);
      setFailed(true);
      setTimeout(() => setFailed(false), FAILED_MS);
    }
    qc.invalidateQueries({ queryKey: CONVERSATIONS_KEY });
  };

  // like the other sheets with fixed heights: the head on its own, then the
  // scroll view as a sibling, so the sheet can hand it the drag
  return (
    <>
      <View collapsable={false} style={styles.top}>
        <SheetHeader title="Розмови" />
        {failed ? (
          <Animated.View entering={FadeIn.duration(160)} exiting={FadeOut.duration(160)}>
            <Text variant="rowCaption" tone="danger" style={styles.failed}>
              Не вдалося видалити
            </Text>
          </Animated.View>
        ) : null}
      </View>
      {conversations.isPending ? (
        <ActivityIndicator style={styles.message} />
      ) : conversations.isError ? (
        <Text tone="danger" style={styles.message}>
          Не вдалося завантажити розмови
        </Text>
      ) : items.length === 0 ? (
        <Text tone="faint" style={styles.message}>
          Тут з’являться твої розмови з асистентом
        </Text>
      ) : (
        // a sheet is a window of its own, so swipes need their own root here
        <GestureHandlerRootView style={styles.fill}>
          <ScrollView contentContainerStyle={styles.list} keyboardShouldPersistTaps="handled">
            {items.map((item, i) => (
              // a deleted chat fades out and the ones below move up into its place
              <Animated.View key={item.id} exiting={FadeOut.duration(160)} layout={LIST_MOVE}>
                {i > 0 ? <View style={[styles.divider, { backgroundColor: withAlpha(c.shade, 0.07) }]} /> : null}
                <ChatHistoryRow
                  title={names[item.id] ?? item.title ?? 'Нова розмова'}
                  when={whenLabel(seconds(item.updated_at))}
                  selected={item.id === current}
                  onOpen={() => open(item.id)}
                  onRename={(title) => setChatTitle(item.id, title)}
                  onDelete={() => remove(item.id)}
                />
              </Animated.View>
            ))}
          </ScrollView>
        </GestureHandlerRootView>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  top: { paddingTop: 22, paddingHorizontal: 20, paddingBottom: 6 },
  failed: { textAlign: 'center', marginTop: 4 },
  message: { paddingVertical: 32, paddingHorizontal: 20, textAlign: 'center' },
  list: { paddingBottom: 24 },
  divider: { height: 1, marginHorizontal: 20 },
});
