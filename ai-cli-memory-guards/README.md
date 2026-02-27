# ai-cli-memory-guards

Local package that installs launcher wrappers:

- `codex-guard`
- `claude-guard`
- `gemini-guard`
- `copilot-guard`

Each wrapper applies `NODE_OPTIONS` memory limits before invoking the real CLI.

## Build and install

```bash
cd ~/pkgbuilds/ai-cli-memory-guards
makepkg -si
```

## Track with paru

```bash
paru -Qm | rg ai-cli-memory-guards
```

## Configure defaults

Edit `/etc/ai-cli-memory-guards.conf`.
