import { useQuery } from '@tanstack/react-query';
import { getCalendars } from 'expo-localization';
import { z } from 'zod';

import { api, openStream, request } from './client';

const int = z.number().int();

const ConversationSchema = z.object({
  id: int,
  // the chat's first question, null until one is asked
  title: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

const MessageSchema = z.object({
  id: int,
  role: z.enum(['user', 'assistant']),
  text: z.string(),
  created_at: z.string(),
});

const MessagesSchema = z.object({
  items: z.array(MessageSchema),
  has_more: z.boolean(),
});

export type Conversation = z.infer<typeof ConversationSchema>;
export type ChatMessage = z.infer<typeof MessageSchema>;
export type Messages = z.infer<typeof MessagesSchema>;

export const CONVERSATIONS_KEY = ['assistant', 'conversations'];
export const messagesKey = (id: number) => ['assistant', 'messages', id];

// a long chat loads its latest messages, older ones aren't paged in yet
const HISTORY_LIMIT = 100;

// newest first
export function useConversations() {
  return useQuery({
    queryKey: CONVERSATIONS_KEY,
    queryFn: () => api(z.array(ConversationSchema), '/assistant/conversations'),
  });
}

// oldest first
export function useMessages(id: number | null) {
  return useQuery({
    queryKey: messagesKey(id ?? 0),
    queryFn: () => api(MessagesSchema, `/assistant/conversations/${id}/messages?limit=${HISTORY_LIMIT}`),
    enabled: id !== null,
  });
}

export const createConversation = () => api(ConversationSchema, '/assistant/conversations', { method: 'POST' });

export const deleteConversation = (id: number) => request(`/assistant/conversations/${id}`, { method: 'DELETE' });

// What the server sends while it answers: a step it takes (with a line for
// the user), a piece of the text, the end, or why it stopped.
const EVENTS = {
  tool: z.object({ name: z.string(), label: z.string() }),
  delta: z.object({ text: z.string() }),
  done: z.object({
    message_id: int.nullable(),
    stop_reason: z.string().nullable(),
  }),
  error: z.object({
    code: z.enum(['timeout', 'model_unavailable', 'internal']),
    detail: z.string(),
  }),
};

type EventName = keyof typeof EVENTS;
export type ReplyEvent = {
  [K in EventName]: { type: K } & z.infer<(typeof EVENTS)[K]>;
}[EventName];

const isEventName = (name: string): name is EventName => name in EVENTS;

// one SSE block: "event: delta\ndata: {...}"
function parseEvent(block: string): ReplyEvent | null {
  let name = '';
  const data: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) name = line.slice(6).trim();
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }
  if (!isEventName(name)) return null;
  try {
    const parsed = EVENTS[name].safeParse(JSON.parse(data.join('\n')));
    return parsed.success ? ({ type: name, ...parsed.data } as ReplyEvent) : null;
  } catch {
    return null;
  }
}

// so "today" and "this week" mean the user's, not Kyiv's
const timezone = () => getCalendars()[0]?.timeZone ?? undefined;

// Sends a message and calls onEvent for each event until the reply ends.
export async function streamReply(
  conversationId: number,
  text: string,
  signal: AbortSignal,
  onEvent: (event: ReplyEvent) => void,
) {
  const body = await openStream(
    `/assistant/conversations/${conversationId}/messages`,
    { text, context: { timezone: timezone() } },
    signal,
  );
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut = buffer.indexOf('\n\n');
    while (cut >= 0) {
      const event = parseEvent(buffer.slice(0, cut));
      buffer = buffer.slice(cut + 2);
      if (event) onEvent(event);
      cut = buffer.indexOf('\n\n');
    }
  }
}
