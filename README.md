# .agents

Portable, cross-harness [Agent Skills](https://agentskills.io/specification) —
one collection, read by multiple AI coding agents.

This repo lives at `~/.agents`, so it is both the public source of truth and the
live user-level skills install. Skills placed here are picked up automatically by
harnesses that scan `~/.agents/skills/`.

## Supported harnesses

| Harness | Reads `~/.agents/skills/`? | Reads `AGENTS.md`? |
|---------|:--------------------------:|:------------------:|
| [OpenCode](https://opencode.ai) | Yes | Yes |
| [pi.dev](https://pi.dev) | Yes | Yes |

`skills/` is the only directory harnesses agree on under `.agents/`; see
[`AGENTS.md`](AGENTS.md) for the directory contract.

## Layout

```text
skills/
  <skill-name>/
    SKILL.md      # required: YAML frontmatter (name, description) + instructions
    references/   # optional
    scripts/      # optional
    assets/       # optional
```

## Adding a skill

1. Create `skills/<skill-name>/SKILL.md` with `name` (kebab-case, matching the
   directory) and a `description` covering what it does and when to use it.
2. Run the checks: `prek run --all-files`.
3. Commit.

## Development

Quality gates run via [`prek`](https://github.com/j178/prek) (pre-commit
compatible) locally and in GitHub Actions:

- markdownlint-cli2 + pymarkdown — Markdown linting
- linkspector — broken-link checking
- yamlfmt — YAML formatting
- actionlint — workflow linting
- `.scripts/validate_skills.py` — SKILL.md frontmatter validation

```sh
prek install      # enable the git hook (already installed here)
prek run --all-files
```

## License

[MIT](LICENSE)
