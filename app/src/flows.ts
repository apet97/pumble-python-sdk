// Read/browse/search/thread flows: pure logic plus a small controller.
//
// Every server interaction goes through the bridge (one MCP path, no
// direct network access). The controller deduplicates identical
// in-flight requests, keeps stale data visible when a refetch fails,
// and turns every failure into a typed UI error state.

import type { Bridge } from "./bridge";
import type { Store } from "./state";
import type { UiError } from "./state";

export const PAGE_LIMIT = 50;
export const SEARCH_LIMIT = 25;

export type ErrorKind = "auth" | "rate_limited" | "recoverable";

export function classifyFailure(failure: {
  reason?: string;
  summary?: string;
}): ErrorKind {
  const text = `${failure.reason ?? ""} ${failure.summary ?? ""}`.toLowerCase();
  if (
    text.includes("auth") ||
    text.includes("permission") ||
    text.includes("401") ||
    text.includes("403")
  ) {
    return "auth";
  }
  if (text.includes("rate") || text.includes("429")) {
    return "rate_limited";
  }
  return "recoverable";
}

export function toUiError(failure: {
  reason?: string;
  summary?: string;
}): UiError {
  return {
    kind: classifyFailure(failure),
    summary: failure.summary ?? "The request failed.",
  };
}

interface RawMessage {
  id?: unknown;
  channel_id?: unknown;
  author?: unknown;
  text?: unknown;
  timestamp_milli?: unknown;
}

export interface Message {
  id: string;
  channelId: string;
  author: string;
  text: string;
  timestampMilli: number | undefined;
}

export function toMessage(raw: RawMessage): Message {
  return {
    id: typeof raw.id === "string" ? raw.id : "",
    channelId: typeof raw.channel_id === "string" ? raw.channel_id : "",
    author: typeof raw.author === "string" ? raw.author : "",
    text: typeof raw.text === "string" ? raw.text : "",
    timestampMilli:
      typeof raw.timestamp_milli === "number" ? raw.timestamp_milli : undefined,
  };
}

function messageList(value: unknown): Message[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => toMessage((item ?? {}) as RawMessage));
}

/** The controller: bridge calls in, store updates out. */
export interface Flows {
  loadBootstrap(): Promise<void>;
  selectChannel(channelId: string): Promise<void>;
  loadMoreMessages(): Promise<void>;
  runSearch(query: string): Promise<void>;
  openThread(channelId: string, messageId: string): Promise<void>;
  back(): void;
  setChannelFilter(value: string): void;
}

export function createFlows(bridge: Bridge, store: Store): Flows {
  const inFlight = new Set<string>();

  async function once<T>(
    key: string,
    run: () => Promise<T>,
  ): Promise<T | undefined> {
    if (inFlight.has(key)) {
      return undefined;
    }
    inFlight.add(key);
    try {
      return await run();
    } finally {
      inFlight.delete(key);
    }
  }

  return {
    async loadBootstrap(): Promise<void> {
      await once("bootstrap", async () => {
        const outcome = await bridge.callTool("pumble_ui_bootstrap");
        if (!outcome.ok || outcome.data["ok"] !== true) {
          store.update({
            phase: "error",
            error: toUiError(outcome.ok ? outcome.data : outcome),
          });
          return;
        }
        const data = outcome.data;
        store.update({
          phase: "ready",
          identity: data["identity"] as Record<string, string>,
          channels: (data["channels"] ?? []) as import("./state").ChannelSummary[],
          users: (data["users"] as Record<string, string>) ?? {},
        });
      });
    },

    async selectChannel(channelId: string): Promise<void> {
      store.update({
        selectedChannelId: channelId,
        pane: "messages",
        messages: {
          items: [],
          nextCursor: null,
          loading: true,
          stale: false,
          error: undefined,
        },
      });
      await once(`page:${channelId}:first`, async () => {
        const outcome = await bridge.callTool("pumble_ui_channel_page", {
          channel_id: channelId,
          limit: PAGE_LIMIT,
        });
        const current = store.get().messages;
        if (!outcome.ok || outcome.data["ok"] !== true) {
          store.update({
            messages: {
              ...current,
              loading: false,
              stale: current.items.length > 0,
              error: toUiError(outcome.ok ? outcome.data : outcome),
            },
          });
          return;
        }
        store.update({
          messages: {
            items: messageList(outcome.data["messages"]),
            nextCursor: (outcome.data["next_cursor"] as string | null) ?? null,
            loading: false,
            stale: false,
            error: undefined,
          },
        });
      });
    },

    async loadMoreMessages(): Promise<void> {
      const state = store.get();
      const channelId = state.selectedChannelId;
      const cursor = state.messages.nextCursor;
      if (channelId === undefined || cursor === null) {
        return;
      }
      await once(`page:${channelId}:${cursor}`, async () => {
        const outcome = await bridge.callTool("pumble_ui_channel_page", {
          channel_id: channelId,
          limit: PAGE_LIMIT,
          cursor,
        });
        const current = store.get().messages;
        if (!outcome.ok || outcome.data["ok"] !== true) {
          store.update({
            messages: {
              ...current,
              loading: false,
              stale: true,
              error: toUiError(outcome.ok ? outcome.data : outcome),
            },
          });
          return;
        }
        store.update({
          messages: {
            items: [...current.items, ...messageList(outcome.data["messages"])],
            nextCursor: (outcome.data["next_cursor"] as string | null) ?? null,
            loading: false,
            stale: false,
            error: undefined,
          },
        });
      });
    },

    async runSearch(query: string): Promise<void> {
      if (query.trim() === "") {
        store.update({
          search: {
            query,
            results: [],
            loading: false,
            error: {
              kind: "recoverable",
              summary: "Type a search query first.",
            },
          },
        });
        return;
      }
      store.update({
        search: { query, results: [], loading: true, error: undefined },
      });
      await once(`search:${query}`, async () => {
        const outcome = await bridge.callTool("search_messages", {
          text: query,
          limit: SEARCH_LIMIT,
        });
        if (!outcome.ok || outcome.data["ok"] === false) {
          store.update({
            search: {
              query,
              results: [],
              loading: false,
              error: toUiError(outcome.ok ? outcome.data : outcome),
            },
          });
          return;
        }
        store.update({
          search: {
            query,
            results: messageList(outcome.data["hits"]),
            loading: false,
            error: undefined,
          },
        });
      });
    },

    async openThread(channelId: string, messageId: string): Promise<void> {
      store.update({
        pane: "thread",
        thread: {
          root: undefined,
          replies: [],
          loading: true,
          error: undefined,
        },
      });
      await once(`thread:${channelId}:${messageId}`, async () => {
        const outcome = await bridge.callTool("pumble_ui_thread", {
          channel_id: channelId,
          message_id: messageId,
        });
        if (!outcome.ok || outcome.data["ok"] !== true) {
          store.update({
            thread: {
              root: undefined,
              replies: [],
              loading: false,
              error: toUiError(outcome.ok ? outcome.data : outcome),
            },
          });
          return;
        }
        store.update({
          thread: {
            root: toMessage((outcome.data["root"] ?? {}) as RawMessage),
            replies: messageList(outcome.data["replies"]),
            loading: false,
            error: undefined,
          },
        });
      });
    },

    back(): void {
      const pane = store.get().pane;
      if (pane === "thread") {
        store.update({ pane: "messages" });
      } else if (pane === "messages") {
        store.update({ pane: "channels" });
      }
    },

    setChannelFilter(value: string): void {
      store.update({ channelFilter: value });
    },
  };
}
