DESIGN
======

File-based task structure and CLI command reference for `tasker`.

---

## Task Model

Two levels: **stories** (root) and **tasks** (within a story).

- A **story** (`s01`) is a root-level unit of work, roughly equivalent to a user story or feature.
- A **task** (`s01t01`) belongs to exactly one story. Task numbering is continuous within the story and carries no hierarchical meaning.

> Future: epics may be introduced (`e01s02t03`), but for now the two-level model is sufficient.

### Story Forms

| Form | Structure | When to use |
|---|---|---|
| Simple | `sNN-short-name.md` | Story with no separate task files |
| Simple with subtasks | `sNN-short-name.md` with `## Subtasks` section | Inline bullet tasks |
| Detailed | `sNN-short-name/README.md` + `sNNtMM-short-name.md` … | Tasks that each need their own description |

Stories **auto-upgrade** when structure requires it:
- Adding inline subtasks → simple with subtasks
- Adding a detailed task → detailed form (dir is created, existing file becomes `README.md`)

Tasks are always files (never directories).

---

## Task ID Scheme

Stories use an `s` prefix followed by a zero-padded number:

```
s01   s02   s03   …
```

Tasks within a story append a `t`-prefixed zero-padded number:

```
s01t01   s01t02   s01t03   …
```

Task numbers are continuous within the story and carry no hierarchical meaning. There is no deeper nesting.

---

## Filename Format

Every file includes a short summary slug appended to the ID:

```
s01-design-file-structure.md
s01-design-file-structure/        ← detailed form (dir)
  README.md
  s01t01-define-task-forms.md
  s01t02-write-cli-spec.md
```

**Rules:**
- Slug is kebab-cased, max 5 words
- Derived automatically from the task title, or set explicitly via `--slug`
- The slug is cosmetic — tasks are always addressed by ID alone (`s01`, `s01t02`)
- When referencing a task in commands, both forms are accepted:
  - `s01` — ID only
  - `s01-design-file-structure` — full filename stem (slug ignored for lookup)

---

## File Structure

### Simple story

```
planning/
  s01-design-file-structure.md
```

### Simple story with subtasks

```
planning/
  s01-design-file-structure.md    ← contains ## Subtasks bullet list
```

### Detailed story

```
planning/
  s01-design-file-structure/
    README.md                     ← story description + list of task links
    s01t01-define-task-forms.md
    s01t02-write-cli-spec.md
```

Root-level stories live directly under `planning/`. Archived stories move to `planning/archive/`.

---

## Task File Format

```
Title
=====

Optional description text.
Can span multiple paragraphs.

## Props

Status: pending
Depends:
- s02 - must finish auth before starting this

## Subtasks

- [ ] pending subtask
- [~] in-progress subtask
- [x] finished subtask
```

**`## Props`** — required `Status:`, optional `Depends:`

| Status value | Meaning |
|---|---|
| `pending` | not started |
| `in-progress` | being worked on |
| `done` | finished |

**`## Subtasks`** — present in the "simple with subtasks" form only. Each line is a checkbox entry.

For the **detailed** form, `README.md` lists tasks as links:

```
## Subtasks

- [ ] [s01t01](s01t01-define-task-forms.md): Define task forms
- [~] [s01t02](s01t02-write-cli-spec.md): Write CLI spec
- [x] [s01t03](s01t03-finished-task.md): Finished task
```

---

## Checkbox Symbols

| Symbol | Status |
|---|---|
| `- [ ]` | pending |
| `- [~]` | in-progress |
| `- [x]` | done |

---

## CLI Commands

### Add tasks

```bash
# Add a root-level story (slug auto-derived from title)
tasker task add <title>

# Add a root-level story with explicit slug
tasker task add <title> --slug <slug>

# Add an inline subtask to a story
tasker task add <story-id> <title>

# Add a detailed task file (auto-upgrades story to detailed form if needed)
tasker task add <story-id> <title> --detail

# Add with explicit slug (e.g. when created by AI)
tasker task add <story-id> <title> --detail --slug <slug>
```

### Upgrade story form

```bash
# Promote a simple story to detailed form (creates sNN-slug/ dir)
tasker task upgrade <story-id>
```

### Update task status

```bash
# Mark in-progress
tasker task start <task-id>

# Mark done (fails if task has open subtasks)
tasker task done <task-id>

# Force close even with open subtasks
tasker task done <task-id> --force-close
```

### List and query

```bash
# List all stories with status summary
tasker list

# List tasks within a story
tasker list <story-id>

# Tasks with all dependencies satisfied
tasker list --ready

# Tasks blocked by unfinished dependencies
tasker list --blocked
```

### Archive

```bash
# Move story to planning/archive/
tasker archive <story-id>
```

Only stories can be archived. Archiving a task is an error.

> **TBD:** Archiving of individual tasks may be supported in the future.

---

## Examples

```bash
# Create a story — slug auto-derived as "design-file-structure"
tasker task add "Design file structure"
# → planning/s01-design-file-structure.md  (Status: pending)

# Add tasks
tasker task add s01 "Define task forms"
# → inline subtask in planning/s01-design-file-structure.md ## Subtasks

tasker task add s01 "Write CLI spec" --detail
# → auto-upgrades to planning/s01-design-file-structure/README.md
# → creates planning/s01-design-file-structure/s01t02-write-cli-spec.md

# AI-created task with explicit slug
tasker task add s01 "Implement command parsing for the new task subcommands" --slug "impl-command-parsing" --detail
# → planning/s01-design-file-structure/s01t03-impl-command-parsing.md

# Reference by ID or full name — both work
tasker task start s01t02
tasker task start s01t02-write-cli-spec

# Close workflow
tasker task done s01t02
tasker task done s01
# Error: s01 has open subtasks. Use --force-close to override.

tasker task done s01t01
tasker task done s01
```
