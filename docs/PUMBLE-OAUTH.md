# Pumble OAuth (marketplace apps)

For apps installed from the Pumble marketplace that act with
user-granted scopes. Distinct from the MCP server's own remote
authorization (which is standard OAuth bearer verification of the MCP
client — see [MCP.md](MCP.md)).

## Flow

```python
from pumble_keys.pumble_app.oauth import (
    create_pumble_oauth_access_token_request,
    create_pumble_oauth_authorization_url,
    verify_pumble_oauth_callback,
)

# 1. Send the user to the consent page.
url = create_pumble_oauth_authorization_url(
    client_id="my-app-client-id",
    redirect_url="https://my.app.example.com/oauth/callback",
    user_scopes=["messages:read"],
    bot_scopes=["messages:write"],   # sent as "bot:messages:write"
    state="anti-csrf-nonce",
)

# 2. Verify the callback (state check + code extraction).
callback = verify_pumble_oauth_callback(
    "https://my.app.example.com/oauth/callback?code=abc&state=anti-csrf-nonce",
    expected_state="anti-csrf-nonce",
)

# 3. Exchange the code: POST the returned form as multipart/form-data.
request = create_pumble_oauth_access_token_request(
    client_id="my-app-client-id",
    client_secret="…from your secret store…",
    code=callback.code,
)
# request.url, request.method == "POST", request.form
# (fields: client-id, client-secret, code)
```

## Rules

- The client secret and every issued token stay server-side; nothing in
  this package logs or persists them (`token_store` offers an in-memory
  store with an injectable persistent backend).
- Always pass and verify `state`.
- Rotate credentials on `APP_UNAUTHORIZED` / `APP_UNINSTALLED` webhook
  events (see [WEBHOOKS.md](WEBHOOKS.md)).
