# The Pumble MCP App

One interactive app ships with the server: `ui://pumble/workspace/v1/index.html`,
opened by the model-visible tool `open_pumble_workspace`. Hosts without
MCP Apps support get the same tool with a structured/text fallback.

## Architecture

- `app/` — plain TypeScript + Vite + the official
  `@modelcontextprotocol/ext-apps` SDK. No React, no CDN, no external
  requests: the production build is one self-contained HTML file.
- `src/pumble_keys/mcp_server/app.py` — registers the `Apps()` extension:
  the `ui://` resource (MIME `text/html;profile=mcp-app`, closed CSP,
  no iframe permissions) for the app-enabled profiles (`curated`,
  `curated-interactive`).
- `src/pumble_keys/mcp_server/app_tools.py` — the opening tool plus the
  app-only helpers (`pumble_ui_bootstrap`, `pumble_ui_channel_page`,
  `pumble_ui_thread`, `_meta.ui.visibility: ["app"]`). All data flows
  through the same façade layer as the curated tools.

## Writes

The composer supports channel messages and thread replies only. Every
send is a two-step sequence: `*_preview` (shows resolved target,
redacted excerpt, risk, expiry, and the full-text sha256 prefix), then
an explicit `*_confirmed` call carrying the unchanged request, preview,
and signed token. Edits invalidate the preview; a failed confirm is
never auto-repeated; the token is never rendered or stored.

## Packaging pipeline

Run before the Python wheel build:

```bash
uv run python tools/build_app.py         # npm build → app_assets/ + manifest
uv run python tools/build_app.py --check # freshness gate (used by CI/pack)
```

The manifest (`app_assets/manifest.json`) pins the sha256 of the
packaged HTML and of the app source tree. `--check` fails when the
source changed without a rebuild or the packaged bytes drifted, so a
stale asset cannot ship. `tests/pack/test_app_asset.py` runs the same
checks under pytest.

## Host integration

- Theme and locale arrive via the host context; the app re-renders in
  place (`data-theme`, `lang`) without reloading.
- No fixed viewport: desktop shows three panes; under 640 px the app
  becomes one navigable pane with a Back control.
- `aria-live` announces phase changes; errors are assertive.

## Accessibility

Automated checks (`app/test/accessibility.test.ts`): labeled inputs,
native buttons only, labeled section landmarks, visible
`:focus-visible` outline, `prefers-reduced-motion` support, and WCAG AA
contrast for both palettes.

Manual checklist (run on a real host before release):

- [ ] Tab reaches every control in a sensible order; Enter/Space
      activates buttons; no keyboard trap.
- [ ] Focus outline is visible on every control in light and dark.
- [ ] Screen reader announces pane names, message authors, and the
      preview card fields.
- [ ] 200 % zoom keeps all controls reachable (no horizontal trap).
- [ ] Dark and light host themes both render with readable contrast
      (visual snapshot).
- [ ] Reduced-motion OS setting produces no animation.
