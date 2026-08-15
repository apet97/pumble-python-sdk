// Browser entry: wire the real ext-apps `App` to the bridge, the store,
// the flows controller, and the renderer. Everything testable lives in
// bridge/state/flows/render; this file alone touches the real host.

import { App } from "@modelcontextprotocol/ext-apps";
import "./styles.css";
import { createBridge } from "./bridge";
import { createFlows } from "./flows";
import { render } from "./render";
import { createStore } from "./state";
import type { HostApp } from "./types";

const NARROW_QUERY = "(max-width: 640px)";

async function start(): Promise<void> {
  const root = document.getElementById("root");
  if (root === null) {
    return;
  }

  const app = new App({ name: "pumble-keys-app", version: "0.1.0" }, {});
  // The ext-apps App satisfies the structural HostApp contract.
  const bridge = createBridge(app as unknown as HostApp);
  const store = createStore();
  const flows = createFlows(bridge, store);
  store.subscribe((state) => render(root, state, flows));

  const media = window.matchMedia(NARROW_QUERY);
  store.update({ narrow: media.matches });
  media.addEventListener("change", (event) => {
    store.update({ narrow: event.matches });
  });

  bridge.onHostContext((context) => store.applyHostContext(context));

  const connectFailure = await bridge.start();
  if (connectFailure !== undefined) {
    store.update({ phase: "error", error: connectFailure });
    return;
  }

  const initial = await bridge.initialResult();
  if (!initial.ok) {
    store.update({ phase: "error", error: initial });
    return;
  }
  store.update({ bootstrap: initial.data });
  await flows.loadBootstrap();
}

void start();
