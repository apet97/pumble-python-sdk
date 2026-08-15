# Search tips

`search_messages` returns exactly one bounded page (default 10, max
50). Narrow with `from_user` or `in_channel` instead of raising the
limit. For channel history, use `get_channel_context` and follow its
explicit `next_cursor`.
