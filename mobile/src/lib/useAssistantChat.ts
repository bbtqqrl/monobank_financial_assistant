import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  CONVERSATIONS_KEY,
  createConversation,
  messagesKey,
  streamReply,
  useConversations,
  useMessages,
  type ReplyEvent,
} from '@/api/assistant';
import { ApiError } from '@/api/client';
import { failure, settle } from '@/lib/haptics';
import { createStore } from '@/lib/store';

// a step the assistant took: the tool and the line shown for it
export type Step = { name: string; label: string };

// The reply being written: the question (until the server has it), what's
// come in so far, the steps it took, and why it stopped, if it did.
export type PendingReply = {
  question: string | null;
  text: string;
  steps: Step[];
  error: string | null;
  // what "Спробувати ще" sends again
  retry: string | null;
  busy: boolean;
  // the user stopped it halfway
  stopped?: boolean;
};

// The open chat, shared with the history sheet: undefined follows the
// latest one, null is a new one not sent yet
export const openChat = createStore<number | null | undefined>(undefined);

// Steps aren't stored with the history, so the ones seen in this session are
// kept here by message id, for the "N кроки" line under an answer
const stepsByMessage = new Map<number, Step[]>();
export const stepsOf = (messageId: number) => stepsByMessage.get(messageId);

const REPLY_ERRORS: Record<Extract<ReplyEvent, { type: 'error' }>['code'], string> = {
  timeout: 'Відповідь забрала забагато часу. Спробуй спитати простіше',
  model_unavailable: 'Асистент зараз недоступний. Спробуй за хвилину',
  internal: 'Не вдалося відповісти. Спробуй ще раз',
};

function sendError(error: unknown) {
  if (error instanceof ApiError && error.status === 429)
    return 'На сьогодні повідомлення закінчились, повертайся завтра';
  if (error instanceof ApiError && error.status === 409) return 'Асистент ще відповідає на попереднє';
  return 'Не вдалося надіслати. Перевір інтернет і спробуй ще раз';
}

// The assistant tab's chat: the open conversation, its history and the reply
// that's streaming in.
export function useAssistantChat() {
  const qc = useQueryClient();
  const conversations = useConversations();
  const picked = openChat.useValue();
  const id = picked === undefined ? (conversations.data?.[0]?.id ?? null) : picked;
  const messages = useMessages(id);
  const [pending, setPending] = useState<PendingReply | null>(null);
  // tools behind the latest finished answer, for the follow-up chips
  const [lastTools, setLastTools] = useState<string[]>([]);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => () => abort.current?.abort(), []);

  // another chat picked in the history: the reply here belongs to the old one
  useEffect(() => {
    if (abort.current) return;
    setPending(null);
    setLastTools([]);
  }, [id]);

  const update = (patch: Partial<PendingReply>) => setPending((p) => (p ? { ...p, ...patch } : p));

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || abort.current) return;
      const controller = new AbortController();
      abort.current = controller;
      setLastTools([]);
      setPending({ question: text, text: '', steps: [], error: null, retry: null, busy: true });

      let chat = id;
      let saved = false;
      let failed = false;
      const steps: Step[] = [];
      try {
        if (chat === null) {
          chat = (await createConversation()).id;
          qc.setQueryData(messagesKey(chat), { items: [], has_more: false });
          openChat.set(chat);
        }
        await streamReply(chat, text, controller.signal, (event) => {
          // the server saves the question before it starts answering
          saved = true;
          if (event.type === 'tool') {
            steps.push({ name: event.name, label: event.label });
            update({ steps: [...steps] });
          } else if (event.type === 'delta') {
            setPending((p) => (p ? { ...p, text: p.text + event.text } : p));
          } else if (event.type === 'done') {
            if (event.message_id !== null && steps.length > 0) stepsByMessage.set(event.message_id, [...steps]);
          } else {
            failed = true;
            update({ error: REPLY_ERRORS[event.code], retry: text });
          }
        });
      } catch (error) {
        // stopped by the user: what came in stays as it is
        if (controller.signal.aborted) return;
        failed = true;
        update(saved ? { error: REPLY_ERRORS.internal, retry: text } : { error: sendError(error), retry: text });
      } finally {
        if (abort.current === controller) abort.current = null;
      }

      if (failed) failure();
      else settle();
      // the history now has the question and the answer
      if (chat !== null) await qc.invalidateQueries({ queryKey: messagesKey(chat) });
      qc.invalidateQueries({ queryKey: CONVERSATIONS_KEY });
      setLastTools(failed ? [] : steps.map((s) => s.name));
      setPending((p) => {
        if (!p?.error) return null;
        // a saved question shows from the history, a failed send keeps it here
        return { ...p, question: saved ? null : p.question, busy: false };
      });
    },
    [id, qc],
  );

  // The server finishes the answer anyway and keeps it, so the full text
  // shows up from the history next time; here it just stops where it is.
  const stop = useCallback(async () => {
    abort.current?.abort();
    abort.current = null;
    setPending((p) => (p ? { ...p, busy: false, stopped: true } : p));
    if (id === null) return;
    // the question is saved by now, so it shows from the history and doesn't
    // vanish when the next one is sent
    await qc.invalidateQueries({ queryKey: messagesKey(id) });
    qc.invalidateQueries({ queryKey: CONVERSATIONS_KEY });
    setPending((p) => (p?.stopped ? { ...p, question: null } : p));
  }, [id, qc]);

  const startNew = useCallback(() => {
    if (abort.current) return;
    openChat.set(null);
  }, []);

  return {
    id,
    messages: messages.data?.items ?? [],
    loading: (picked === undefined && conversations.isPending) || (id !== null && messages.isPending),
    failed:
      (picked === undefined && conversations.isError && !conversations.data) || (messages.isError && !messages.data),
    reload: () => (conversations.isError ? conversations.refetch() : messages.refetch()),
    pending,
    busy: !!pending?.busy,
    lastTools,
    send,
    stop,
    startNew,
  };
}
