// Browser entry: wire the real ext-apps `App` to the bridge, the store,
// and the renderer. Everything testable lives in bridge/state/render;
// this file is the only one that touches the real host transport.

import { App } from "@modelcontextprotocol/ext-apps";
import "./styles.css";
import { createBridge } from "./bridge";
import { createStore } from "./state";
import { render } from "./render";
import type { HostApp } from "./types";

async function start(): Promise<void> {
  const root = document.getElementById("root");
  if (root === null) {
    return;
  }

  const app = new App(
    { name: "pumble-keys-app", version: "0.1.0" },
    {},
  );
  // The ext-apps App satisfies the structural HostApp contract.
  const bridge = createBridge(app as unknown as HostApp);
  const store = createStore();
  store.subscribe((state) => render(root, state));
  render(root, store.get());

  bridge.onHostContext((context) => store.applyHostContext(context));

  const connectFailure = await bridge.start();
  if (connectFailure !== undefined) {
    store.update({ phase: "error", error: connectFailure });
    return;
  }

  const initial = await bridge.initialResult();
  if (initial.ok) {
    store.update({ phase: "ready", bootstrap: initial.data });
  } else {
    store.update({ phase: "error", error: initial });
  }
}

void start();
