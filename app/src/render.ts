// DOM rendering. All dynamic values reach the page through
// `textContent` — never innerHTML — so Pumble content cannot inject
// markup. Desktop shows three panes; narrow mode shows one pane with a
// back control.

import type { Composer } from "./composer";
import type { Flows } from "./flows";
import type { UiError, ViewState } from "./state";
import { authorLabel, filteredChannels } from "./state";

function el(tag: string, className: string, text?: string): HTMLElement {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

function errorLine(error: UiError): HTMLElement {
  const label =
    error.kind === "auth"
      ? "Not authorized"
      : error.kind === "rate_limited"
        ? "Rate limited"
        : "Error";
  return el("p", `status status-error error-${error.kind}`, `${label}: ${error.summary}`);
}

function messageItem(
  state: ViewState,
  message: { id: string; channelId: string; author: string; text: string },
  flows: Flows,
): HTMLElement {
  const item = el("li", "message");
  item.dataset["messageId"] = message.id;
  item.append(el("span", "author", authorLabel(state, message.author)));
  item.append(el("span", "text", message.text));
  const open = el("button", "open-thread", "Thread");
  open.addEventListener("click", () => {
    void flows.openThread(message.channelId, message.id);
  });
  item.append(open);
  return item;
}


function composerSection(state: ViewState, composer: Composer): HTMLElement {
  const section = el("section", "composer");
  const c = state.composer;
  section.append(
    el(
      "h3",
      "composer-title",
      c.mode === "reply" ? "Reply in thread" : "New message",
    ),
  );

  const channelInput = el("input", "composer-channel") as HTMLInputElement;
  channelInput.placeholder = "Channel";
  channelInput.value = c.channel;
  channelInput.addEventListener("input", () => {
    composer.setChannel(channelInput.value);
  });
  section.append(channelInput);

  const textArea = document.createElement("textarea");
  textArea.className = "composer-text";
  textArea.value = c.text;
  textArea.addEventListener("input", () => {
    composer.setText(textArea.value);
  });
  section.append(textArea);

  const previewButton = el(
    "button",
    "composer-preview",
    "Preview",
  ) as HTMLButtonElement;
  previewButton.disabled = c.busy;
  previewButton.addEventListener("click", () => {
    void composer.requestPreview();
  });
  section.append(previewButton);

  if (c.card !== undefined) {
    const card = el("div", "preview-card");
    card.append(el("p", "preview-target", `To: ${c.card.targetLabel}`));
    card.append(el("p", "preview-excerpt", `Text: ${c.card.excerpt}`));
    card.append(el("p", "preview-risk", `Risk: ${c.card.risk}`));
    card.append(
      el("p", "preview-hash", `Full-text sha256 ${c.card.hashPrefix}…`),
    );
    card.append(
      el(
        "p",
        "preview-expiry",
        `Expires at ${new Date(c.card.expiresAtMs).toISOString()}`,
      ),
    );
    const confirmButton = el(
      "button",
      "composer-confirm",
      "Confirm and send",
    ) as HTMLButtonElement;
    confirmButton.disabled = c.busy;
    confirmButton.addEventListener("click", () => {
      void composer.confirm();
    });
    card.append(confirmButton);
    section.append(card);
  }

  if (c.needsNewPreview) {
    section.append(
      el(
        "p",
        "status",
        "The send failed. Review and request a new preview; nothing is retried automatically.",
      ),
    );
  }
  if (c.error !== undefined) {
    section.append(errorLine(c.error));
  }
  if (c.receipt !== undefined) {
    const receipt = el("div", "receipt");
    receipt.append(el("p", "receipt-summary", c.receipt.summary));
    receipt.append(
      el(
        "p",
        `receipt-verification verification-${c.receipt.verificationState}`,
        `Verification: ${c.receipt.verificationState}` +
          (c.receipt.verificationDetail === undefined
            ? ""
            : ` (${c.receipt.verificationDetail})`),
      ),
    );
    section.append(receipt);
  }
  return section;
}

function channelsPane(state: ViewState, flows: Flows): HTMLElement {
  const pane = el("section", "pane pane-channels");
  pane.append(el("h2", "pane-title", "Channels"));
  if (state.identity !== undefined) {
    pane.append(el("p", "identity", `Signed in as ${state.identity["name"]}`));
  }
  const filter = el("input", "channel-filter") as HTMLInputElement;
  filter.type = "search";
  filter.placeholder = "Filter channels";
  filter.value = state.channelFilter;
  pane.append(filter);
  const list = el("ul", "channel-list");
  const channels = filteredChannels(state);
  if (channels.length === 0) {
    pane.append(el("p", "status", "No channels."));
  }
  for (const channel of channels) {
    const item = el("li", "channel");
    const button = el(
      "button",
      "channel-open",
      `#${channel.name} (${channel.channel_type})`,
    );
    button.dataset["channelId"] = channel.id;
    button.addEventListener("click", () => {
      void flows.selectChannel(channel.id);
    });
    item.append(button);
    list.append(item);
  }
  pane.append(list);
  return pane;
}

function messagesPane(
  state: ViewState,
  flows: Flows,
  composer: Composer,
): HTMLElement {
  const pane = el("section", "pane pane-messages");
  pane.append(el("h2", "pane-title", "Messages"));

  const searchBox = el("input", "search-input") as HTMLInputElement;
  searchBox.type = "search";
  searchBox.placeholder = "Search messages";
  searchBox.value = state.search.query;
  const searchButton = el("button", "search-run", "Search");
  searchButton.addEventListener("click", () => {
    void flows.runSearch(searchBox.value);
  });
  pane.append(searchBox, searchButton);

  if (state.search.error !== undefined) {
    pane.append(errorLine(state.search.error));
  }
  if (state.search.loading) {
    pane.append(el("p", "status", "Searching…"));
  }
  if (state.search.results.length > 0) {
    const results = el("ul", "search-results");
    for (const hit of state.search.results) {
      results.append(messageItem(state, hit, flows));
    }
    pane.append(results);
  }

  const messages = state.messages;
  if (messages.stale) {
    pane.append(el("p", "status status-stale", "Showing possibly stale data."));
  }
  if (messages.error !== undefined) {
    pane.append(errorLine(messages.error));
  }
  if (messages.loading) {
    pane.append(el("p", "status", "Loading messages…"));
  } else if (
    messages.items.length === 0 &&
    state.selectedChannelId !== undefined &&
    messages.error === undefined
  ) {
    pane.append(el("p", "status", "No messages in this channel."));
  }
  const list = el("ul", "message-list");
  for (const message of messages.items) {
    list.append(messageItem(state, message, flows));
  }
  pane.append(list);
  if (messages.nextCursor !== null) {
    const more = el("button", "load-more", "Load older messages");
    more.addEventListener("click", () => {
      void flows.loadMoreMessages();
    });
    pane.append(more);
  }
  if (state.composer.mode === "message") {
    pane.append(composerSection(state, composer));
  }
  return pane;
}

function threadPane(
  state: ViewState,
  flows: Flows,
  composer: Composer,
): HTMLElement {
  const pane = el("section", "pane pane-thread");
  pane.append(el("h2", "pane-title", "Thread"));
  const thread = state.thread;
  if (thread.error !== undefined) {
    pane.append(errorLine(thread.error));
  }
  if (thread.loading) {
    pane.append(el("p", "status", "Loading thread…"));
  }
  if (thread.root !== undefined) {
    const list = el("ul", "thread-list");
    list.append(messageItem(state, thread.root, flows));
    for (const reply of thread.replies) {
      list.append(messageItem(state, reply, flows));
    }
    pane.append(list);
  }
  if (state.composer.mode === "reply") {
    pane.append(composerSection(state, composer));
  }
  return pane;
}

export function render(
  root: HTMLElement,
  state: ViewState,
  flows: Flows,
  composer: Composer,
): void {
  root.replaceChildren();
  root.dataset["theme"] = state.theme;
  root.dataset["pane"] = state.pane;
  root.dataset["narrow"] = state.narrow ? "true" : "false";

  const shell = el("main", "shell");

  if (state.phase === "connecting") {
    shell.append(el("p", "status", "Connecting to the host…"));
    root.append(shell);
    return;
  }
  if (state.phase === "error") {
    const failure = state.error;
    shell.append(
      el(
        "p",
        "status status-error",
        failure !== undefined && "summary" in failure
          ? failure.summary
          : "Something went wrong.",
      ),
    );
    root.append(shell);
    return;
  }

  if (state.narrow) {
    if (state.pane !== "channels") {
      const back = el("button", "back", "Back");
      back.addEventListener("click", () => flows.back());
      shell.append(back);
    }
    if (state.pane === "channels") {
      shell.append(channelsPane(state, flows));
    } else if (state.pane === "messages") {
      shell.append(messagesPane(state, flows, composer));
    } else {
      shell.append(threadPane(state, flows, composer));
    }
  } else {
    shell.append(
      channelsPane(state, flows),
      messagesPane(state, flows, composer),
      threadPane(state, flows, composer),
    );
  }
  root.append(shell);
}
