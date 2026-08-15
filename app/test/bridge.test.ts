// P35 bridge unit tests: a fake host stands in for the ext-apps App.

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { createBridge, toOutcome } from "../src/bridge";
import { createStore, initialState } from "../src/state";
import type {
  HostApp,
  HostContextLike,
  ToolResultLike,
} from "../src/types";

class FakeHost implements HostApp {
  ontoolresult: ((params: ToolResultLike) => void) | undefined;
  onhostcontextchanged:
    | ((params: { context?: HostContextLike }) => void)
    | undefined;

  connectError: Error | undefined;
  callError: Error | undefined;
  callResult: ToolResultLike = { structuredContent: { ok: true } };
  context: HostContextLike | undefined;
  calls: Array<{ name: string; arguments?: Record<string, unknown> }> = [];

  async connect(): Promise<void> {
    if (this.connectError !== undefined) {
      throw this.connectError;
    }
  }

  async callServerTool(params: {
    name: string;
    arguments?: Record<string, unknown>;
  }): Promise<ToolResultLike> {
    this.calls.push(params);
    if (this.callError !== undefined) {
      throw this.callError;
    }
    return this.callResult;
  }

  getHostContext(): HostContextLike | undefined {
    return this.context;
  }
}

describe("toOutcome", () => {
  it("unwraps the union envelope", () => {
    const outcome = toOutcome({
      structuredContent: { result: { ok: true, id: "x" } },
    });
    expect(outcome).toEqual({ ok: true, data: { ok: true, id: "x" } });
  });

  it("passes plain structured content through", () => {
    const outcome = toOutcome({ structuredContent: { ok: true, n: 1 } });
    expect(outcome).toEqual({ ok: true, data: { ok: true, n: 1 } });
  });

  it("maps isError to a tool_error value with the text content", () => {
    const outcome = toOutcome({
      isError: true,
      content: [{ type: "text", text: "rate limited" }],
    });
    expect(outcome).toEqual({
      ok: false,
      reason: "tool_error",
      summary: "rate limited",
    });
  });

  it("flags missing or non-object structured content", () => {
    expect(toOutcome({}).ok).toBe(false);
    const bad = toOutcome({
      structuredContent: { result: "just text" },
    });
    expect(bad.ok).toBe(false);
    if (!bad.ok) {
      expect(bad.reason).toBe("malformed_result");
    }
  });
});

describe("createBridge", () => {
  it("resolves the initial result from the first toolresult", async () => {
    const host = new FakeHost();
    const bridge = createBridge(host);
    host.ontoolresult?.({ structuredContent: { result: { ok: true } } });
    // A second push must not replace the first outcome.
    host.ontoolresult?.({ structuredContent: { result: { ok: false } } });
    await expect(bridge.initialResult()).resolves.toEqual({
      ok: true,
      data: { ok: true },
    });
  });

  it("returns protocol failures from start as values", async () => {
    const host = new FakeHost();
    host.connectError = new Error("no host");
    const bridge = createBridge(host);
    const outcome = await bridge.start();
    expect(outcome?.reason).toBe("protocol_error");
  });

  it("calls tools with name and arguments and unwraps the result", async () => {
    const host = new FakeHost();
    host.callResult = { structuredContent: { result: { ok: true, n: 2 } } };
    const bridge = createBridge(host);
    const outcome = await bridge.callTool("find_channel", { channel: "x" });
    expect(outcome).toEqual({ ok: true, data: { ok: true, n: 2 } });
    expect(host.calls).toEqual([
      { name: "find_channel", arguments: { channel: "x" } },
    ]);
  });

  it("never throws on protocol errors from callServerTool", async () => {
    const host = new FakeHost();
    host.callError = new Error("disconnected");
    const bridge = createBridge(host);
    const outcome = await bridge.callTool("whoami");
    expect(outcome.ok).toBe(false);
    if (!outcome.ok) {
      expect(outcome.reason).toBe("protocol_error");
      expect(outcome.summary).toContain("whoami");
    }
  });

  it("replays the current host context and forwards changes", () => {
    const host = new FakeHost();
    host.context = { theme: "dark", locale: "de" };
    const bridge = createBridge(host);
    const seen: HostContextLike[] = [];
    bridge.onHostContext((context) => seen.push(context));
    host.onhostcontextchanged?.({ context: { theme: "light" } });
    host.onhostcontextchanged?.({});
    expect(seen).toEqual([
      { theme: "dark", locale: "de" },
      { theme: "light" },
    ]);
  });
});

describe("store", () => {
  it("applies host context without clobbering unknown fields", () => {
    const store = createStore();
    store.applyHostContext({ theme: "dark" });
    expect(store.get().theme).toBe("dark");
    expect(store.get().locale).toBe(initialState().locale);
    store.applyHostContext({ locale: "fr" });
    expect(store.get().theme).toBe("dark");
    expect(store.get().locale).toBe("fr");
  });

  it("notifies subscribers on every update", () => {
    const store = createStore();
    const phases: string[] = [];
    store.subscribe((state) => phases.push(state.phase));
    store.update({ phase: "ready" });
    store.update({ phase: "error" });
    expect(phases).toEqual(["ready", "error"]);
  });
});

describe("memory-only state policy", () => {
  it("no persistent browser storage API appears in app sources", () => {
    const srcDir = join(__dirname, "..", "src");
    const banned = [
      "localStorage",
      "sessionStorage",
      "indexedDB",
      "document.cookie",
    ];
    for (const file of readdirSync(srcDir)) {
      const text = readFileSync(join(srcDir, file), "utf-8");
      for (const needle of banned) {
        expect(text.includes(needle), `${file} uses ${needle}`).toBe(false);
      }
    }
  });
});
