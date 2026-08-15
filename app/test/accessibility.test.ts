// @vitest-environment happy-dom
// P39 accessibility and host-integration checks.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { createComposer } from "../src/composer";
import { createFlows } from "../src/flows";
import { render } from "../src/render";
import { createStore } from "../src/state";
import type { Bridge } from "../src/bridge";
import type { ToolOutcome } from "../src/types";

const nullBridge: Bridge = {
  async start() {
    return undefined;
  },
  async initialResult(): Promise<ToolOutcome> {
    return { ok: true, data: {} };
  },
  async callTool(): Promise<ToolOutcome> {
    return { ok: true, data: { ok: true } };
  },
  onHostContext() {},
};

function ready() {
  const store = createStore();
  store.update({
    phase: "ready",
    channels: [{ id: "c-1", name: "engineering", channel_type: "PUBLIC" }],
  });
  const flows = createFlows(nullBridge, store);
  const composer = createComposer(nullBridge, store);
  const root = document.createElement("div");
  const draw = () => render(root, store.get(), flows, composer);
  draw();
  return { store, root, draw };
}

describe("semantic controls and labels", () => {
  it("every input and textarea carries an accessible label", () => {
    const { root } = ready();
    for (const control of root.querySelectorAll("input, textarea")) {
      expect(
        control.getAttribute("aria-label"),
        control.className,
      ).toBeTruthy();
    }
  });

  it("all actions are native buttons (keyboard reachable)", () => {
    const { root } = ready();
    expect(root.querySelectorAll("button").length).toBeGreaterThan(0);
    // No click handlers on non-interactive elements: actions are buttons
    // or inputs only, so tab order and Enter/Space work by default.
    expect(root.querySelectorAll("[onclick]")).toHaveLength(0);
  });

  it("panes are labeled landmarks", () => {
    const { root } = ready();
    for (const pane of root.querySelectorAll(".pane")) {
      expect(pane.tagName.toLowerCase()).toBe("section");
      expect(pane.getAttribute("aria-label")).toBeTruthy();
    }
  });
});

describe("host integration without reload", () => {
  it("theme and locale changes re-render in place", () => {
    const { store, root, draw } = ready();
    expect(root.dataset["theme"]).toBe("light");
    store.applyHostContext({ theme: "dark", locale: "de" });
    draw();
    expect(root.dataset["theme"]).toBe("dark");
    expect(root.getAttribute("lang")).toBe("de");
  });

  it("narrow and wide layouts render from the same state", () => {
    const { store, root, draw } = ready();
    expect(root.querySelectorAll(".pane")).toHaveLength(3);
    store.update({ narrow: true });
    draw();
    expect(root.querySelectorAll(".pane")).toHaveLength(1);
  });
});

function relativeLuminance(hex: string): number {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((offset) => {
    const channel = parseInt(value.slice(offset, offset + 2), 16) / 255;
    return channel <= 0.03928
      ? channel / 12.92
      : ((channel + 0.055) / 1.055) ** 2.4;
  });
  const [r, g, b] = channels as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(fg: string, bg: string): number {
  const [light, dark] = [relativeLuminance(fg), relativeLuminance(bg)].sort(
    (a, b) => b - a,
  ) as [number, number];
  return (light + 0.05) / (dark + 0.05);
}

describe("styles", () => {
  const css = readFileSync(join(__dirname, "..", "src", "styles.css"), "utf-8");

  it("declares visible focus and reduced-motion support", () => {
    expect(css).toContain(":focus-visible");
    expect(css).toContain("prefers-reduced-motion");
  });

  it("light and dark palettes meet WCAG AA contrast", () => {
    // Palette pairs from styles.css tokens.
    expect(contrast("#1a1d21", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#5c6066", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#b3261e", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#f4f5f6", "#1a1d21")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#a8adb3", "#1a1d21")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#ff8a80", "#1a1d21")).toBeGreaterThanOrEqual(4.5);
    // Accent / state tokens (buttons, active channel, risk chip,
    // verified receipt) in both palettes.
    expect(contrast("#4141c8", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#ffffff", "#4141c8")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#4141c8", "#ececfb")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#1e6b3a", "#e7f4ec")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#7a4d00", "#fdf3e0")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#9fa4ff", "#1a1d21")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#14142e", "#9fa4ff")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#8fd8ab", "#1e3328")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#f2c078", "#3a2f1a")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#5c6066", "#f6f7f9")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#a8adb3", "#22262c")).toBeGreaterThanOrEqual(4.5);
  });
});
