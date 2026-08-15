// Typed host bridge: the only path between the shell and the MCP host.
//
// Responsibilities:
// - connect to the host and surface connection failures as values;
// - hand the shell the opening tool's result (the host pushes it as a
//   `toolresult` notification after `connect`);
// - wrap `callServerTool` so protocol errors and tool errors both come
//   back as `BridgeFailure` values, never exceptions;
// - fan host context (theme/locale) to a listener, replaying the
//   current context on subscribe.
//
// The bridge holds no credentials and persists nothing.

import type {
  BridgeFailure,
  HostApp,
  HostContextLike,
  ToolOutcome,
  ToolResultLike,
} from "./types";

function failure(
  reason: BridgeFailure["reason"],
  summary: string,
): BridgeFailure {
  return { ok: false, reason, summary };
}

function firstText(result: ToolResultLike): string {
  for (const block of result.content ?? []) {
    if (block.type === "text" && typeof block.text === "string") {
      return block.text;
    }
  }
  return "";
}

/** Unwrap the server's `{"result": ...}` union envelope when present. */
function unwrap(structured: Record<string, unknown>): unknown {
  const keys = Object.keys(structured);
  if (keys.length === 1 && keys[0] === "result") {
    return structured["result"];
  }
  return structured;
}

export function toOutcome(result: ToolResultLike): ToolOutcome {
  if (result.isError) {
    return failure("tool_error", firstText(result) || "The tool call failed.");
  }
  const structured = result.structuredContent;
  if (structured === undefined) {
    return failure(
      "malformed_result",
      "The tool result carried no structured content.",
    );
  }
  const data = unwrap(structured);
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    return failure(
      "malformed_result",
      "The structured tool result is not an object.",
    );
  }
  return { ok: true, data: data as Record<string, unknown> };
}

export interface Bridge {
  /** Connect to the host; a failed handshake is a value, not a throw. */
  start(): Promise<BridgeFailure | undefined>;
  /** Resolves with the opening tool's result (or a failure value). */
  initialResult(): Promise<ToolOutcome>;
  /** One server tool call; never throws. */
  callTool(
    name: string,
    args?: Record<string, unknown>,
  ): Promise<ToolOutcome>;
  /** Subscribe to host context; replays the current context if known. */
  onHostContext(listener: (context: HostContextLike) => void): void;
}

export function createBridge(host: HostApp): Bridge {
  let resolveInitial: (outcome: ToolOutcome) => void;
  const initial = new Promise<ToolOutcome>((resolve) => {
    resolveInitial = resolve;
  });
  let initialSettled = false;

  host.ontoolresult = (params) => {
    if (!initialSettled) {
      initialSettled = true;
      resolveInitial(toOutcome(params));
    }
  };

  const contextListeners: Array<(context: HostContextLike) => void> = [];
  host.onhostcontextchanged = (params) => {
    const context = params.context;
    if (context !== undefined) {
      for (const listener of contextListeners) {
        listener(context);
      }
    }
  };

  return {
    async start(): Promise<BridgeFailure | undefined> {
      try {
        await host.connect();
        return undefined;
      } catch (error) {
        return failure(
          "protocol_error",
          `Connecting to the host failed: ${String(error)}`,
        );
      }
    },

    initialResult(): Promise<ToolOutcome> {
      return initial;
    },

    async callTool(
      name: string,
      args?: Record<string, unknown>,
    ): Promise<ToolOutcome> {
      let result: ToolResultLike;
      try {
        result = await host.callServerTool({
          name,
          arguments: args ?? {},
        });
      } catch (error) {
        return failure(
          "protocol_error",
          `Tool ${name} failed at the protocol layer: ${String(error)}`,
        );
      }
      return toOutcome(result);
    },

    onHostContext(listener: (context: HostContextLike) => void): void {
      contextListeners.push(listener);
      const current = host.getHostContext();
      if (current !== undefined) {
        listener(current);
      }
    },
  };
}
