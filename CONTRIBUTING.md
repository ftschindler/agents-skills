# Contributing

Thanks for adding to this collection of portable [Agent Skills](https://agentskills.io/specification).

## Adding a skill

1. Create a directory `skills/<skill-name>/` — kebab-case, and the name must match
   the `name` field in your frontmatter.
2. Add a `SKILL.md` with YAML frontmatter:

   ```markdown
   ---
   name: my-skill
   description: What it does and WHEN to use it, including the trigger phrases a
     model should match on.
   ---

   # My Skill

   Instructions the agent follows when the skill is loaded.
   ```

   Required frontmatter: `name` and `description`. Optional spec fields
   (`license`, `allowed-tools`, `disallowed-tools`, `compatibility`) are
   type-checked when present.
3. Put supporting material in optional subdirectories — `references/`, `scripts/`,
   `assets/`. Keep the skill self-contained.

Write the `description` for a model, not a human index: state the task and the
situations that should trigger it. This is what harnesses use to decide when to
load the skill.

## Directory contract

`skills/` is the only directory under `.agents/` that harnesses read by
convention. Do not add sibling directories (`commands/`, `rules/`, `agents/`,
`mcp/`) — nothing loads them from here. See [`AGENTS.md`](AGENTS.md) for details.

## Before you commit

Run the quality gates locally:

```sh
prek run --all-files
```

These also run in CI. They check:

- Markdown linting (markdownlint-cli2, pymarkdown)
- Broken links (linkspector)
- YAML formatting (yamlfmt) and workflow linting (actionlint)
- `SKILL.md` frontmatter against the Agent Skills spec

If you have not enabled the git hook yet:

```sh
prek install
```

## Conventions

- Filenames are lowercase with no whitespace (convention filenames such as
  `SKILL.md`, `README.md`, `AGENTS.md`, `LICENSE` are exempt).
- Text files use LF line endings (enforced by `.gitattributes` and
  `.editorconfig`).
- Never commit secrets or files from outside the `skills/` tree — `.gitignore`
  denies everything by default and allow-lists only skills and repo infra.

By contributing you agree that your work is licensed under the repository's
[MIT License](LICENSE).
