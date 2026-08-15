// In-memory view state. Nothing is persisted to any browser storage —
// the state dies with the iframe, so no API key, confirmation token,
// or message body can outlive the session (a test enforces this).

import type { BridgeFailure, HostContextLike } from "./types";

export type Phase = "connecting" | "ready" | "error";

export interface ViewState {
  phase: Phase;
  theme: string;
  locale: string;
  /** Structured payload of the opening tool (identity, counts, flags). */
  bootstrap: Record<string, unknown> | undefined;
  error: BridgeFailure | undefined;
}

export function initialState(): ViewState {
  return {
    phase: "connecting",
    theme: "light",
    locale: "en",
    bootstrap: undefined,
    error: undefined,
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
