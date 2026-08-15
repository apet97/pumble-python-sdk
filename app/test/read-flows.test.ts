// @vitest-environment happy-dom
// P37 read/browse/search/thread flow tests with a fake bridge.

import { describe, expect, it } from "vitest";
import type { Bridge } from "../src/bridge";
import { classifyFailure, createFlows } from "../src/flows";
import { render } from "../src/render";
import { authorLabel, createStore, filteredChannels } from "../src/state";
import type { ToolOutcome } from "../src/types";

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

function message(id: string, text = "hello", author = "u-1") {
  return {
    id,
    channel_id: "c-1",
    author,
    text,
    timestamp_milli: 1,
  };
}

function setup() {
  const bridge = new FakeBridge();
  const store = createStore();
  store.update({ phase: "ready" });
  const flows = createFlows(bridge, store);
  return { bridge, store, flows };
}

describe("classifyFailure", () => {
  it("maps auth, rate-limit, and everything else", () => {
    expect(classifyFailure({ summary: "HTTP 401 permission denied" })).toBe(
      "auth",
    );
    expect(classifyFailure({ summary: "Too many requests (429)" })).toBe(
      "rate_limited",
    );
    expect(classifyFailure({ reason: "rate-limit" })).toBe("rate_limited");
    expect(classifyFailure({ reason: "api_error", summary: "boom" })).toBe(
      "recoverable",
    );
  });
});

describe("bootstrap", () => {
  it("fills identity, channels, and the author map", async () => {
    const { bridge, store, flows } = setup();
    bridge.respond("pumble_ui_bootstrap", () => ({
      ok: true,
      data: {
        ok: true,
        identity: { id: "u-1", name: "Probe" },
        channels: [
          { id: "c-1", name: "engineering", channel_type: "PUBLIC" },
          { id: "c-2", name: "random", channel_type: "PRIVATE" },
        ],
        users: { "u-1": "Probe" },
      },
    }));
    await flows.loadBootstrap();
    const state = store.get();
    expect(state.identity).toEqual({ id: "u-1", name: "Probe" });
    expect(state.channels).toHaveLength(2);
    expect(authorLabel(state, "u-1")).toBe("Probe");
    expect(authorLabel(state, "u-unknown")).toBe("u-unknown");
    store.update({ channelFilter: "eng" });
    expect(filteredChannels(store.get()).map((c) => c.name)).toEqual([
      "engineering",
    ]);
  });
});

describe("channel paging", () => {
  it("passes the explicit cursor and appends pages", async () => {
    const { bridge, store, flows } = setup();
    bridge.respond("pumble_ui_channel_page", (args) => ({
      ok: true,
      data:
        args["cursor"] === undefined
          ? {
              ok: true,
              messages: [message("m-2"), message("m-1")],
              next_cursor: "m-1",
            }
          : { ok: true, messages: [message("m-0")], next_cursor: null },
    }));
    await flows.selectChannel("c-1");
    expect(store.get().messages.items.map((m) => m.id)).toEqual(["m-2", "m-1"]);
    expect(store.get().messages.nextCursor).toBe("m-1");
    await flows.loadMoreMessages();
    expect(bridge.calls[1]?.args).toEqual({
      channel_id: "c-1",
      limit: 50,
      cursor: "m-1",
    });
    expect(store.get().messages.items.map((m) => m.id)).toEqual([
      "m-2",
      "m-1",
      "m-0",
    ]);
    expect(store.get().messages.nextCursor).toBeNull();
    // No cursor left: loadMore is a no-op.
    await flows.loadMoreMessages();
    expect(bridge.calls).toHaveLength(2);
  });

  it("deduplicates identical in-flight requests", async () => {
    const { bridge, flows } = setup();
    let release: () => void = () => {};
    bridge.gate = new Promise((resolve) => {
      release = resolve;
    });
    bridge.respond("pumble_ui_channel_page", () => ({
      ok: true,
      data: { ok: true, messages: [], next_cursor: null },
    }));
    const first = flows.selectChannel("c-1");
    const second = flows.selectChannel("c-1");
    release();
    await Promise.all([first, second]);
    expect(bridge.calls).toHaveLength(1);
  });

  it("keeps stale items visible when a later page fails", async () => {
    const { bridge, store, flows } = setup();
    let fail = false;
    bridge.respond("pumble_ui_channel_page", () =>
      fail
        ? { ok: false, reason: "protocol_error", summary: "disconnected" }
        : {
            ok: true,
            data: {
              ok: true,
              messages: [message("m-1")],
              next_cursor: "m-1",
            },
          },
    );
    await flows.selectChannel("c-1");
    fail = true;
    await flows.loadMoreMessages();
    const messages = store.get().messages;
    expect(messages.items.map((m) => m.id)).toEqual(["m-1"]);
    expect(messages.stale).toBe(true);
    expect(messages.error?.kind).toBe("recoverable");
  });
});

describe("search", () => {
  it("requires a query and never calls the server without one", async () => {
    const { bridge, store, flows } = setup();
    await flows.runSearch("   ");
    expect(bridge.calls).toHaveLength(0);
    expect(store.get().search.error?.summary).toContain("query");
  });

  it("runs a bounded search and stores hits", async () => {
    const { bridge, store, flows } = setup();
    bridge.respond("search_messages", () => ({
      ok: true,
      data: { ok: true, hits: [message("m-9", "found it")] },
    }));
    await flows.runSearch("found");
    expect(bridge.calls[0]).toEqual({
      name: "search_messages",
      args: { text: "found", limit: 25 },
    });
    expect(store.get().search.results.map((m) => m.text)).toEqual(["found it"]);
  });

  it("surfaces auth failures as the auth error state", async () => {
    const { bridge, store, flows } = setup();
    bridge.respond("search_messages", () => ({
      ok: true,
      data: {
        ok: false,
        reason: "api_error",
        summary: "HTTP 401: permission denied",
      },
    }));
    await flows.runSearch("x");
    expect(store.get().search.error?.kind).toBe("auth");
  });
});

describe("thread", () => {
  it("opens by exact channel and message ids", async () => {
    const { bridge, store, flows } = setup();
    bridge.respond("pumble_ui_thread", () => ({
      ok: true,
      data: {
        ok: true,
        root: message("m-1", "root"),
        replies: [message("m-2", "reply")],
        participants: ["u-1"],
      },
    }));
    await flows.openThread("c-1", "m-1");
    expect(bridge.calls[0]?.args).toEqual({
      channel_id: "c-1",
      message_id: "m-1",
    });
    const state = store.get();
    expect(state.pane).toBe("thread");
    expect(state.thread.root?.text).toBe("root");
    expect(state.thread.replies.map((m) => m.text)).toEqual(["reply"]);
  });

  it("back() walks thread → messages → channels", async () => {
    const { store, flows } = setup();
    store.update({ pane: "thread" });
    flows.back();
    expect(store.get().pane).toBe("messages");
    flows.back();
    expect(store.get().pane).toBe("channels");
    flows.back();
    expect(store.get().pane).toBe("channels");
  });
});

describe("rendering safety", () => {
  function renderState(mutate: (store: ReturnType<typeof createStore>) => void) {
    const { store, flows } = setup();
    mutate(store);
    const root = document.createElement("div");
    render(root, store.get(), flows);
    return root;
  }

  it("escapes hostile message content", () => {
    const payload = '<img src=x onerror="window.x=1"><script>window.y=1</script>';
    const root = renderState((store) => {
      store.update({
        selectedChannelId: "c-1",
        messages: {
          items: [
            {
              id: "m-1",
              channelId: "c-1",
              author: "u-1",
              text: payload,
              timestampMilli: 1,
            },
          ],
          nextCursor: null,
          loading: false,
          stale: false,
          error: undefined,
        },
      });
    });
    expect(root.querySelector("img")).toBeNull();
    expect(root.querySelector("script")).toBeNull();
    expect(root.querySelector(".text")?.textContent).toBe(payload);
  });

  it("shows loading, empty, stale, and error states", () => {
    const loading = renderState((store) => {
      store.update({
        messages: { ...store.get().messages, loading: true },
      });
    });
    expect(loading.textContent).toContain("Loading messages");

    const empty = renderState((store) => {
      store.update({ selectedChannelId: "c-1" });
    });
    expect(empty.textContent).toContain("No messages");

    const stale = renderState((store) => {
      store.update({
        messages: {
          ...store.get().messages,
          stale: true,
          error: { kind: "rate_limited", summary: "429" },
        },
      });
    });
    expect(stale.textContent).toContain("stale");
    expect(stale.querySelector(".error-rate_limited")).not.toBeNull();
  });

  it("narrow mode renders one pane with a back control", () => {
    const narrow = renderState((store) => {
      store.update({ narrow: true, pane: "messages" });
    });
    expect(narrow.querySelectorAll(".pane")).toHaveLength(1);
    expect(narrow.querySelector(".back")).not.toBeNull();

    const wide = renderState(() => {});
    expect(wide.querySelectorAll(".pane")).toHaveLength(3);
    expect(wide.querySelector(".back")).toBeNull();
  });
});
