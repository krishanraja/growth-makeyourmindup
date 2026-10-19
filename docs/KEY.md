# Existing Control Centre credential

Krish confirmed on 17 October 2026 that `GROWTH_ENGINE_TOKEN` is in GitHub
secrets, and Vercel project access is available. A secret's presence does
not prove a particular local runner has it. Never print or copy its value
into a chat, repository, report, issue, log or draft.

Development, evidence preparation, local queues and dry runs need no token:

```powershell
python growth.py doctor --offline
python growth.py dry-run
```

A separately authorised scheduled delivery uses the existing runtime
`GROWTH_ENGINE_TOKEN`, or the existing Windows file:
`%USERPROFILE%\.config\growth-makeyourmindup\token`. The environment takes
precedence. UTF-8 BOM files are supported. Do not regenerate the token,
change GitHub secrets or edit Vercel configuration as part of this upgrade.

GitHub secret values cannot be downloaded through the secrets API. A
GitHub Actions secret is only available inside a workflow explicitly
configured to consume it; it does not automatically appear in a local
Codex session. Never create a workflow to expose a secret. The check
workflow deliberately uses no secrets and makes no Control Centre writes;
only the Control Center loop below reads a secret.

For an already configured production runner, `python growth.py doctor`
performs read-only checks. Missing key, HTTP 401, endpoint failure or absent
social login is reported as an access gap. There is no direct database
fallback. No HTTP redirect is followed with the bearer credential. Remote
error bodies are not echoed. Only the approved Control Centre HTTPS origin
is accepted.

Delivery requires a valid v2 envelope and an explicit `--deliver` in an
independently authorised scheduled job. During this implementation, use
only the dry-run form. Any future credential setup or rotation is a
separate task with its own explicit instruction.

## The engine protocol key

The growth engine protocol uses its own bearer, a `gen1_` token issued for
this engine alone, as `CONTROL_CENTER_ENGINE_TOKEN`. It is a different key
from `GROWTH_ENGINE_TOKEN`. Control Center keeps only its SHA-256.

- On GitHub it is already a repository secret, with `CONTROL_CENTER_URL` as
  a repository variable. Only `.github/workflows/control-center.yml` reads
  them.
- In the publication workspace, `growth.py cc ... --deliver` reads
  `CONTROL_CENTER_ENGINE_TOKEN` from the environment, or else the file
  `%USERPROFILE%\.config\growth-makeyourmindup\engine-token`, beside the
  packs key file. Never commit it, print it or paste it into a chat.
- `python growth.py doctor` checks it read-only (`GET capabilities`) and
  says NOT READY when it is missing or refused.

Issuing a new token replaces the old one at once, so the GitHub secret and
the workspace file must then both change. That is a separate task with
Krish's explicit yes.
