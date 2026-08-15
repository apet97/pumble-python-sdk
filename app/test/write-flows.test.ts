// @vitest-environment happy-dom
// P38 composer tests: preview/confirm binding, invalidation, no retry.

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { Bridge } from "../src/bridge";
import { createComposer } from "../src/composer";
import { createFlows } from "../src/flows";
import { render } from "../src/render";
import { createStore } from "../src/state";
import type { ToolOutcome } from "../src/types";

const TOKEN = "signed-token-not-real-abc123";

type Responder = (args: Record<string, unknown>) => ToolOutcome;

class FakeBridge implements Bridge {
  calls: Array<{ name: string; args: Record<string, unknown> }> = [];
  responders = new Map<string, Responder>();
  gate: Promise<void> | undefined;

  respond(name: string, responder: Responder): void {
    this.responders.set(name, responder);
  }

  async start(): Promise<undefined> {
    return undefined;
  }

  async initialResult(): Promise<ToolOutcome> {
    return { ok: true, data: {} };
  }

  async callTool(
    name: string,
    args?: Record<string, unknown>,
  ): Promise<ToolOutcome> {
    this.calls.push({ name, args: args ?? {} });
    if (this.gate !== undefined) {
      await this.gate;
    }
    const responder = this.responders.get(name);
    if (responder === undefined) {
      return { ok: false, reason: "protocol_error", summary: "no responder" };
    }
    return responder(args ?? {});
  }

  onHostContext(): void {}
}

function previewPayload(text: string): Record<string, unknown> {
  return {
    ok: true,
    summary: "Preview ready.",
    preview: {
      action_type: "send_message",
      target_kind: "channel",
      target_id: "c-1",
      target_name: "engineering",
      text_excerpt: text.slice(0, 160),
      text_sha256: "a".repeat(64),
      risk_level: "normal",
      workspace_id: "ws-fp",
      issued_at_ms: 1000,
      expires_at_ms: 121000,
      request_sha256: "b".repeat(64),
    },
    token: TOKEN,
    next_actions: [],
  };
}

function confirmedPayload(): Record<string, unknown> {
  return {
    ok: true,
    summary: "Sent message m-1 to #engineering.",
    ids: { message_id: "m-1" },
    verification_state: "verified",
    verification_detail: undefined,
  };
}

function setup() {
  const bridge = new FakeBridge();
  const store = createStore();
  store.update({ phase: "ready" });
  const composer = createComposer(bridge, store);
  composer.setChannel("engineering");
  composer.setText("hello world");
  return { bridge, store, composer };
}

describe("preview", () => {
  it("first action is always the preview tool with the exact request", async () => {
    const { bridge, store, composer } = setup();
    bridge.respond("send_message_preview", () => ({
      ok: true,
      data: previewPayload("hello world"),
    }));
    await composer.requestPreview();
    expect(bridge.calls).toEqual([
      {
        name: "send_message_preview",
        args: { channel: "engineering", text: "hello world" },
      },
    ]);
    const card = store.get().composer.card;
    expect(card?.targetLabel).toBe("engineering");
    expect(card?.excerpt).toBe("hello world");
    expect(card?.risk).toBe("normal");
    expect(card?.expiresAtMs).toBe(121000);
    expect(card?.hashPrefix).toBe("a".repeat(12));
  });

  it("does nothing without a channel or text", async () => {
    const { bridge, store, composer } = setup();
    composer.setText("");
    await composer.requestPreview();
    expect(bridge.calls).toHaveLength(0);
    expect(store.get().composer.card).toBeUndefined();
  });
});

describe("confirm", () => {
  async function previewed() {
    const context = setup();
    context.bridge.respond("send_message_preview", () => ({
      ok: true,
      data: previewPayload("hello world"),
    }));
    context.bridge.respond("send_message_confirmed", () => ({
      ok: true,
      data: confirmedPayload(),
    }));
    await context.composer.requestPreview();
    return context;
  }

  it("sends the unchanged request, preview, and token", async () => {
    const { bridge, store, composer } = await previewed();
    await composer.confirm();
    const confirm = bridge.calls[1];
    expect(confirm?.name).toBe("send_message_confirmed");
    expect(confirm?.args["channel"]).toBe("engineering");
    expect(confirm?.args["text"]).toBe("hello world");
    expect(confirm?.args["token"]).toBe(TOKEN);
    expect(confirm?.args["preview"]).toEqual(
      previewPayload("hello world")["preview"],
    );
    const receipt = store.get().composer.receipt;
    expect(receipt?.verificationState).toBe("verified");
    expect(store.get().composer.card).toBeUndefined();
  });

  it("an edit invalidates the preview and blocks confirm", async () => {
    const { bridge, store, composer } = await previewed();
    composer.setText("hello world EDITED");
    expect(store.get().composer.card).toBeUndefined();
    await composer.confirm();
    expect(bridge.calls.map((c) => c.name)).toEqual(["send_message_preview"]);
    expect(store.get().composer.error?.summary).toContain("new preview");
  });

  it("a target edit also invalidates", async () => {
    const { store, composer } = await previewed();
    composer.setChannel("random");
    expect(store.get().composer.card).toBeUndefined();
  });

  it("double-click cannot double-send", async () => {
    const { bridge, composer } = await previewed();
    let release: () => void = () => {};
    bridge.gate = new Promise((resolve) => {
      release = resolve;
    });
    const first = composer.confirm();
    const second = composer.confirm();
    release();
    await Promise.all([first, second]);
    expect(
      bridge.calls.filter((c) => c.name === "send_message_confirmed"),
    ).toHaveLength(1);
  });

  it("server rejection (tamper/expiry) is shown and never auto-retried", async () => {
    const { bridge, store, composer } = await previewed();
    bridge.respond("send_message_confirmed", () => ({
      ok: true,
      data: {
        ok: false,
        reason: "confirmation_expired",
        summary: "The preview expired; request a new preview.",
      },
    }));
    await composer.confirm();
    const state = store.get().composer;
    expect(state.needsNewPreview).toBe(true);
    expect(state.error?.summary).toContain("expired");
    expect(state.card).toBeUndefined();
    // A second confirm cannot re-send: the token is gone.
    await composer.confirm();
    expect(
      bridge.calls.filter((c) => c.name === "send_message_confirmed"),
    ).toHaveLength(1);
  });

  it("transport failure keeps the failure separate from verification", async () => {
    const { bridge, store, composer } = await previewed();
    bridge.respond("send_message_confirmed", () => ({
      ok: false,
      reason: "protocol_error",
      summary: "disconnected",
    }));
    await composer.confirm();
    const state = store.get().composer;
    expect(state.receipt).toBeUndefined();
    expect(state.error?.kind).toBe("recoverable");
    expect(state.needsNewPreview).toBe(true);
  });

  it("reply mode uses the reply tools with the thread root id", async () => {
    const { bridge, composer } = setup();
    composer.setMode("reply", "m-root");
    composer.setChannel("engineering");
    composer.setText("in thread");
    bridge.respond("reply_to_thread_preview", () => ({
      ok: true,
      data: previewPayload("in thread"),
    }));
    bridge.respond("reply_to_thread_confirmed", () => ({
      ok: true,
      data: confirmedPayload(),
    }));
    await composer.requestPreview();
    await composer.confirm();
    expect(bridge.calls.map((c) => c.name)).toEqual([
      "reply_to_thread_preview",
      "reply_to_thread_confirmed",
    ]);
    expect(bridge.calls[0]?.args["message_id"]).toBe("m-root");
    expect(bridge.calls[1]?.args["message_id"]).toBe("m-root");
  });
});

describe("token containment", () => {
  it("the token never appears in the rendered DOM", async () => {
    const bridge = new FakeBridge();
    const store = createStore();
    store.update({ phase: "ready" });
    const flows = createFlows(bridge, store);
    const composer = createComposer(bridge, store);
    composer.setChannel("engineering");
    composer.setText("hello world");
    bridge.respond("send_message_preview", () => ({
      ok: true,
      data: previewPayload("hello world"),
    }));
    await composer.requestPreview();
    const root = document.createElement("div");
    render(root, store.get(), flows, composer);
    expect(root.querySelector(".preview-card")).not.toBeNull();
    expect(root.innerHTML.includes(TOKEN)).toBe(false);
  });

  it("no composer source path stores the token outside memory", () => {
    const srcDir = join(__dirname, "..", "src");
    for (const file of readdirSync(srcDir)) {
      const text = readFileSync(join(srcDir, file), "utf-8");
      expect(text.includes("localStorage"), file).toBe(false);
    }
  });
});
