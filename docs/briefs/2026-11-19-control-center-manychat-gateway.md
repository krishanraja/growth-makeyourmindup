# Brief for Control Center: a read-only ManyChat service for this engine (19 Nov 2026)

From growth-makeyourmindup, which never changes Control Center (AGENTS.md rule 7). Krish chose ManyChat for the
keyword-DM test on 13 Nov and put `MANYCHAT_API_KEY` in Control Center's Vercel production settings. On 19 Nov the API
gateway catalog lists no `manychat` service, so the key has no adapter.

Asked for, granted to `makeyourmindup` only:

| Operation | Use | Bound |
|---|---|---|
| `manychat.page_info` (GET `/fb/page/getInfo`) | Read back that the connected Instagram account is makeyourmind.up | one call, no writes |
| `manychat.flows` (GET `/fb/page/getFlows`) | Check the build sheet's automations exist with the right names | one call, no writes |
| `manychat.tags`, `manychat.custom_fields` (GET) | Read the arms ledger's tags and fields | one call each, no writes |

No send, no flow trigger, no subscriber write, no billing change. ManyChat's API cannot create or edit a keyword
trigger, so the automations are built in its builder from `docs/briefs/2026-11-19-manychat-build-sheet.md`; the
gateway only checks them. Confirm each endpoint against ManyChat's own API reference when building the adapter.
