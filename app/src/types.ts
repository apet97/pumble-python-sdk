// Shared types for the Pumble MCP App shell.
//
// The bridge never throws at callers: every outcome is a value, mirroring
// the Python facade contract. `HostApp` is the structural subset of the
// ext-apps `App` class the shell uses, so tests inject a fake host.

/** A text/other content block inside a tool result. */
export interface ContentBlock {
  type: string;
  text?: string;
}

/** The subset of an MCP `CallToolResult` the shell reads. */
export interface ToolResultLike {
  content?: ContentBlock[];
  structuredContent?: Record<string, unknown>;
  isError?: boolean;
}

/** The subset of the host context the shell reacts to. */
export interface HostContextLike {
  theme?: string;
  locale?: string;
  displayMode?: string;
}

/** Structural subset of `@modelcontextprotocol/ext-apps` `App`. */
export interface HostApp {
  connect(): Promise<void>;
  callServerTool(params: {
    name: string;
    arguments?: Record<string, unknown>;
  }): Promise<ToolResultLike>;
  getHostContext(): HostContextLike | undefined;
  ontoolresult: ((params: ToolResultLike) => void) | undefined;
  onhostcontextchanged:
    | ((params: { context?: HostContextLike }) => void)
    | undefined;
}

/** Successful tool outcome: the structured payload, envelope unwrapped. */
export interface ToolSuccess {
  ok: true;
  data: Record<string, unknown>;
}

/** Any failure, as a value: tool error, protocol error, or bad payload. */
export interface BridgeFailure {
  ok: false;
  reason: "tool_error" | "protocol_error" | "malformed_result";
  summary: string;
}

export type ToolOutcome = ToolSuccess | BridgeFailure;
