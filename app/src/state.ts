// In-memory view state. Nothing is persisted to any browser storage —
// the state dies with the iframe, so no API key, confirmation token,
// or message body can outlive the session (a test enforces this).

import type { ComposerState } from "./composer";
import { initialComposer } from "./composer";
import type { Message } from "./flows";
import type { BridgeFailure, HostContextLike } from "./types";

export type Phase = "connecting" | "ready" | "error";
export type Pane = "channels" | "messages" | "thread";

export interface UiError {
  kind: "auth" | "rate_limited" | "recoverable";
  summary: string;
}

export interface ChannelSummary {
  id: string;
  name: string;
  channel_type: string;
}

export interface MessagesState {
  items: Message[];
  nextCursor: string | null;
  loading: boolean;
  /** True when shown items may be outdated (a refetch failed). */
  stale: boolean;
  error: UiError | undefined;
}

export interface SearchState {
  query: string;
  results: Message[];
  loading: boolean;
  error: UiError | undefined;
}

export interface ThreadState {
  root: Message | undefined;
  replies: Message[];
  loading: boolean;
  error: UiError | undefined;
}

export interface ViewState {
  phase: Phase;
  theme: string;
  locale: string;
  /** Structured payload of the opening tool (identity, counts, flags). */
  bootstrap: Record<string, unknown> | undefined;
  error: BridgeFailure | UiError | undefined;
  identity: Record<string, string> | undefined;
  channels: ChannelSummary[];
  channelFilter: string;
  users: Record<string, string>;
  pane: Pane;
  narrow: boolean;
  selectedChannelId: string | undefined;
  messages: MessagesState;
  search: SearchState;
  thread: ThreadState;
  composer: ComposerState;
}

export function initialState(): ViewState {
  return {
    phase: "connecting",
    theme: "light",
    locale: "en",
    bootstrap: undefined,
    error: undefined,
    identity: undefined,
    channels: [],
    channelFilter: "",
    users: {},
    pane: "channels",
    narrow: false,
    selectedChannelId: undefined,
    messages: {
      items: [],
      nextCursor: null,
      loading: false,
      stale: false,
      error: undefined,
    },
    search: { query: "", results: [], loading: false, error: undefined },
    thread: { root: undefined, replies: [], loading: false, error: undefined },
    composer: initialComposer(),
  };
}

export type Listener = (state: ViewState) => void;

export interface Store {
  get(): ViewState;
  update(patch: Partial<ViewState>): void;
  applyHostContext(context: HostContextLike): void;
  subscribe(listener: Listener): void;
}

export function createStore(state: ViewState = initialState()): Store {
  const listeners: Listener[] = [];

  function emit(): void {
    for (const listener of listeners) {
      listener(state);
    }
  }

  return {
    get(): ViewState {
      return state;
    },
    update(patch: Partial<ViewState>): void {
      state = { ...state, ...patch };
      emit();
    },
    applyHostContext(context: HostContextLike): void {
      state = {
        ...state,
        theme: context.theme ?? state.theme,
        locale: context.locale ?? state.locale,
      };
      emit();
    },
    subscribe(listener: Listener): void {
      listeners.push(listener);
    },
  };
}

/** Case-insensitive channel filter over the bootstrap catalog. */
export function filteredChannels(state: ViewState): ChannelSummary[] {
  const needle = state.channelFilter.trim().toLowerCase();
  if (needle === "") {
    return state.channels;
  }
  return state.channels.filter((channel) =>
    channel.name.toLowerCase().includes(needle),
  );
}

/** Author label: user map name first, raw id as the fallback. */
export function authorLabel(state: ViewState, authorId: string): string {
  return state.users[authorId] ?? authorId;
}
