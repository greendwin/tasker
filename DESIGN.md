DESIGN
======

File-based task structure and CLI command reference for `tasker`.

---

## Task Model

Everything is a **task**. Tasks are recursive — any task can have subtasks of any form at any depth.

### Three Forms

| Form | Structure | When to use |
|---|---|---|
| Simple | `tNN-short-name.md` | Leaf task, no children needed |
| Simple with subtasks | `tNN-short-name.md` with `## Subtasks` section | Inline bullet subtasks |
| Detailed | `tNN-short-name/README.md` + `tNN_MM-short-name.md` … | Subtasks that each need their own description |

Tasks **auto-upgrade** when structure requires it:
- Adding inline subtasks → simple with subtasks
- Adding a detailed subtask → detailed form (dir is created, existing file becomes `README.md`)

---

## Task ID Scheme

Root tasks use a `t` prefix followed by a zero-padded number:

```
t01   t02   t03   …
```

Nested tasks append child numbers with underscores:

```
t01_01   t01_02   t01_02_01   …
```

The `t` prefix appears only at the root level. Children are plain numbers.

---

## Filename Format

Every task file includes a short summary slug appended to the ID:

```
t01-design-file-structure.md
t01_02-write-cli-spec.md
t01-design-file-structure/        ← detailed form (dir)
  README.md
  t01_01-define-task-forms.md
```

**Rules:**
- Slug is kebab-cased, max 5 words
- Derived automatically from the task title, or set explicitly via `--slug`
- The slug is cosmetic — tasks are always addressed by ID alone (`t01`, `t01_02`)
- When referencing a task in commands, both forms are accepted:
  - `t01` — ID only
  - `t01-design-file-structure` — full filename stem (slug ignored for lookup)

---

## File Structure

### Simple task

```
planning/
  t01-design-file-structure.md
```

### Simple task with subtasks

```
planning/
  t01-design-file-structure.md    ← contains ## Subtasks bullet list
```

### Detailed task

```
planning/
  t01-design-file-structure/
    README.md                     ← task description + list of subtask links
    t01_01-define-task-forms.md   ← simple subtask
    t01_02-write-cli-spec/        ← detailed subtask
      README.md
      t01_02_01-draft-commands.md
```

Root-level tasks live directly under `planning/`. Archived tasks move to `planning/archive/`.

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
- t02 - must finish auth before starting this

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

For the **detailed** form, `README.md` lists subtasks as links:

```
## Subtasks

- [ ] [t01_01](t01_01-define-task-forms.md): Define task forms
- [~] [t01_02](t01_02-write-cli-spec/): Write CLI spec
- [x] [t01_03](t01_03-finished-task.md): Finished task
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
# Add a root-level simple task (slug auto-derived from title)
tasker task add <title>

# Add a root-level task with explicit slug
tasker task add <title> --slug <slug>

# Add a simple subtask under a parent
tasker task add <parent-id> <title>

# Add a detailed subtask (auto-upgrades parent to detailed form if needed)
tasker task add <parent-id> <title> --detail

# Add with explicit slug (e.g. when created by AI)
tasker task add <parent-id> <title> --detail --slug <slug>
```

### Upgrade task form

```bash
# Promote a simple task to detailed form (creates tNN-slug/ dir)
tasker task upgrade <task-id>
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
# List all root tasks with status summary
tasker list

# List subtasks of a given task
tasker list <task-id>

# Tasks with all dependencies satisfied
tasker list --ready

# Tasks blocked by unfinished dependencies
tasker list --blocked
```

### Archive

```bash
# Move root task to planning/archive/
tasker archive <task-id>
```

Only root tasks can be archived. Archiving a non-root task is an error.

> **TBD:** Archiving of mid-tree tasks may be supported in the future.

---

## Examples

```bash
# Create a root task — slug auto-derived as "design-file-structure"
tasker task add "Design file structure"
# → planning/t01-design-file-structure.md  (Status: pending)

# Add subtasks
tasker task add t01 "Define task forms"
# → inline subtask in planning/t01-design-file-structure.md ## Subtasks

tasker task add t01 "Write CLI spec" --detail
# → auto-upgrades to planning/t01-design-file-structure/README.md
# → creates planning/t01-design-file-structure/t01_02-write-cli-spec.md

# AI-created task with explicit slug
tasker task add t01 "Implement command parsing for the new task subcommands" --slug "impl-command-parsing" --detail
# → planning/t01-design-file-structure/t01_03-impl-command-parsing.md

# Reference by ID or full name — both work
tasker task start t01_02
tasker task start t01_02-write-cli-spec

# Close workflow
tasker task done t01_02
tasker task done t01
# Error: t01 has open subtasks. Use --force-close to override.

tasker task done t01_01
tasker task done t01
```
