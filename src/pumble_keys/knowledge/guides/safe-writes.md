# Safe writes

Every default write is a two-step flow:

1. Call the preview tool. It resolves the target, shows a redacted
   excerpt and a risk level, and returns a signed confirmation token
   with an expiry. Nothing is sent.
2. Call the confirmed tool with the unchanged request plus the preview
   and token. The server verifies the signature, expiry, workspace
   binding, and request equality, then performs exactly one write.

A confirmed write is never retried. Success is proven by a direct read
of the created object, not by search.
