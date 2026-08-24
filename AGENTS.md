# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

A portable, cross-harness collection of **Agent Skills**. It lives at `~/.agents`
so it doubles as the source of truth (a public git repo) and the live
user-level skills install that agent harnesses load automatically.

## Directory contract

`skills/` is the **only** subdirectory under `.agents/` that harnesses agree on.
Do not invent sibling directories (`commands/`, `rules/`, `agents/`, `mcp/`) —
no tool reads them from here. If you need those, ask the user to revisit
<https://github.com/dyoshikawa/rulesync> rather to generate tool-native files.

```text
skills/
  <skill-name>/          # kebab-case; must equal frontmatter `name`
    SKILL.md             # required; YAML frontmatter + instructions
    references/          # optional supporting docs
    scripts/             # optional helper scripts
    assets/              # optional templates/resources
```

## Authoring a skill

Every `SKILL.md` needs YAML frontmatter with at least `name` and `description`,
per the Agent Skills spec (<https://agentskills.io/specification>):

```markdown
---
name: my-skill
description: One sentence on WHAT it does and WHEN to use it, including trigger phrases.
---

# My Skill
...
```

Rules enforced by pre-commit and CI:

- `name` is kebab-case and matches the directory name.
- `description` is non-empty (used by the model to decide when to load the skill).
- Filenames are lowercase, no whitespace (except `SKILL.md`, `README.md`, etc.).
- Markdown passes markdownlint-cli2 and pymarkdown; links resolve (linkspector).

## Before committing

Run the checks locally:

```sh
prek run --all-files
```

Never commit secrets or files from outside the `skills/` tree — `.gitignore`
denies everything by default and allow-lists only skills and repo infra.
