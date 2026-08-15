// Composer: channel message and thread reply, preview → confirm only.
//
// The first action is always a preview call; the confirm call sends the
// UNCHANGED request + preview + token back to the server, which alone
// enforces signature, expiry, workspace, and text-hash binding. Any
// edit invalidates the held preview. A failed confirmed write is never
// auto-repeated: the user must request a fresh preview. The signed
// token stays in memory and is never rendered.

import type { Bridge } from "./bridge";
import type { Store, UiError } from "./state";
import { toUiError } from "./flows";

export type ComposerMode = "message" | "reply";

export interface PreviewCard {
  targetLabel: string;
  excerpt: string;
  risk: string;
  expiresAtMs: number;
  hashPrefix: string;
}

export interface Receipt {
  summary: string;
  verificationState: string;
  verificationDetail: string | undefined;
}

interface Snapshot {
  mode: ComposerMode;
  channel: string;
  messageId: string | undefined;
  text: string;
}

export interface ComposerState {
  mode: ComposerMode;
  channel: string;
  messageId: string | undefined;
  text: string;
  busy: boolean;
  card: PreviewCard | undefined;
  error: UiError | undefined;
  receipt: Receipt | undefined;
  /** True after a failed confirm: a new preview is required. */
  needsNewPreview: boolean;
}

export function initialComposer(): ComposerState {
  return {
    mode: "message",
    channel: "",
    messageId: undefined,
    text: "",
    busy: false,
    card: undefined,
    error: undefined,
    receipt: undefined,
    needsNewPreview: false,
  };
}

export interface Composer {
  setMode(mode: ComposerMode, messageId?: string): void;
  setChannel(channel: string): void;
  setText(text: string): void;
  requestPreview(): Promise<void>;
  confirm(): Promise<void>;
}

export function createComposer(bridge: Bridge, store: Store): Composer {
  // The token and the exact previewed request live here, outside the
  // rendered state, so no render path can leak them into the DOM.
  let token: string | undefined;
  let preview: Record<string, unknown> | undefined;
  let snapshot: Snapshot | undefined;

  function get(): ComposerState {
    return store.get().composer;
  }

  function patch(partial: Partial<ComposerState>): void {
    store.update({ composer: { ...get(), ...partial } });
  }

  function invalidate(): void {
    token = undefined;
    preview = undefined;
    snapshot = undefined;
    patch({ card: undefined });
  }

  function matchesSnapshot(state: ComposerState): boolean {
    return (
      snapshot !== undefined &&
      snapshot.mode === state.mode &&
      snapshot.channel === state.channel &&
      snapshot.messageId === state.messageId &&
      snapshot.text === state.text
    );
  }

  return {
    setMode(mode: ComposerMode, messageId?: string): void {
      invalidate();
      patch({
        mode,
        messageId: mode === "reply" ? messageId : undefined,
        receipt: undefined,
        error: undefined,
        needsNewPreview: false,
      });
    },

    setChannel(channel: string): void {
      if (channel !== get().channel) {
        invalidate();
      }
      patch({ channel });
    },

    setText(text: string): void {
      if (text !== get().text) {
        invalidate();
      }
      patch({ text });
    },

    async requestPreview(): Promise<void> {
      const state = get();
      if (state.busy || state.channel.trim() === "" || state.text === "") {
        return;
      }
      patch({ busy: true, error: undefined, receipt: undefined });
      const isReply = state.mode === "reply";
      const args: Record<string, unknown> = {
        channel: state.channel,
        text: state.text,
      };
      if (isReply) {
        args["message_id"] = state.messageId;
      }
      const outcome = await bridge.callTool(
        isReply ? "reply_to_thread_preview" : "send_message_preview",
        args,
      );
      if (!outcome.ok || outcome.data["ok"] !== true) {
        invalidate();
        patch({
          busy: false,
          error: toUiError(outcome.ok ? outcome.data : outcome),
        });
        return;
      }
      const data = outcome.data;
      preview = data["preview"] as Record<string, unknown>;
      token = data["token"] as string;
      snapshot = {
        mode: state.mode,
        channel: state.channel,
        messageId: state.messageId,
        text: state.text,
      };
      patch({
        busy: false,
        needsNewPreview: false,
        card: {
          targetLabel: String(preview["target_name"] ?? preview["target_id"]),
          excerpt: String(preview["text_excerpt"] ?? ""),
          risk: String(preview["risk_level"] ?? ""),
          expiresAtMs: Number(preview["expires_at_ms"] ?? 0),
          hashPrefix: String(preview["text_sha256"] ?? "").slice(0, 12),
        },
      });
    },

    async confirm(): Promise<void> {
      const state = get();
      if (state.busy) {
        return;
      }
      if (
        token === undefined ||
        preview === undefined ||
        !matchesSnapshot(state)
      ) {
        invalidate();
        patch({
          error: {
            kind: "recoverable",
            summary: "The preview no longer matches; request a new preview.",
          },
        });
        return;
      }
      patch({ busy: true, error: undefined });
      const isReply = state.mode === "reply";
      const args: Record<string, unknown> = {
        channel: state.channel,
        text: state.text,
        preview,
        token,
      };
      if (isReply) {
        args["message_id"] = state.messageId;
      }
      const outcome = await bridge.callTool(
        isReply ? "reply_to_thread_confirmed" : "send_message_confirmed",
        args,
      );
      if (!outcome.ok || outcome.data["ok"] !== true) {
        // Never auto-repeat a failed confirmed write.
        invalidate();
        patch({
          busy: false,
          needsNewPreview: true,
          error: toUiError(outcome.ok ? outcome.data : outcome),
        });
        return;
      }
      const data = outcome.data;
      invalidate();
      patch({
        busy: false,
        text: "",
        receipt: {
          summary: String(data["summary"] ?? "Sent."),
          verificationState: String(data["verification_state"] ?? "unknown"),
          verificationDetail:
            typeof data["verification_detail"] === "string"
              ? data["verification_detail"]
              : undefined,
        },
      });
    },
  };
}
