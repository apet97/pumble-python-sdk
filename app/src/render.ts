// DOM rendering for the shell. All dynamic values reach the page
// through `textContent` — never innerHTML — so Pumble content cannot
// inject markup. P37 builds the full layout on top of this skeleton.

import type { ViewState } from "./state";

function el(
  tag: string,
  className: string,
  text?: string,
): HTMLElement {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

export function render(root: HTMLElement, state: ViewState): void {
  root.replaceChildren();
  root.dataset["theme"] = state.theme;

  const shell = el("main", "shell");
  shell.append(el("h1", "title", "Pumble workspace"));

  if (state.phase === "connecting") {
    shell.append(el("p", "status", "Connecting to the host…"));
  } else if (state.phase === "error") {
    shell.append(
      el(
        "p",
        "status status-error",
        state.error?.summary ?? "Something went wrong.",
      ),
    );
  } else {
    const bootstrap = state.bootstrap ?? {};
    const name = typeof bootstrap["name"] === "string" ? bootstrap["name"] : "";
    shell.append(
      el(
        "p",
        "status",
        name === "" ? "Connected." : `Connected as ${name}.`,
      ),
    );
  }

  root.append(shell);
}
