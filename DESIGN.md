DESIGN
======

File-based task structure and CLI command reference for `tasker`.

---

## Task Model

Everything is a **task**. Tasks are recursive — any task can have subtasks at any depth.

- A **story** (`s01`) is a root-level task. Story numbers are unlimited (`s01`, `s02`, … `s123`).
- **Subtasks** extend the parent ID by appending two digits after `t`. Each level adds exactly two digits, giving a limit of 99 siblings per parent.

### Task Forms

| Form | Structure | When to use |
|---|---|---|
| Inline | ID + title in parent's `## Subtasks` bullet list | Leaf task, no description needed |
| Basic | `sNN-short-name.md` | Task needing description or inline subtasks |
| Extended | `sNN-short-name/README.md` + child files … | Subtasks that each need their own file |

All tasks have an ID regardless of form. A slug (and therefore a filename) is only needed when a task has its own file (basic or extended form).

Tasks **auto-upgrade** when structure requires it:
- Promoting an inline task to have a description → basic form (file created)
- Adding a subtask with `--details` to a basic task → extended form (dir is created, existing file becomes `README.md`)

---

## Task ID Scheme

Stories use an `s` prefix followed by a zero-padded number (no upper limit):

```
s01   s02   s03   …   s123   …
```

Subtasks extend the parent ID with `t` (first level only) and then append two digits per nesting level:

```
s01t01          ← task 01 inside story s01
s01t0102        ← subtask 02 inside task s01t01
s01t010203      ← sub-subtask 03 inside task s01t0102
```

Rules:
- The `t` separator appears once, immediately after the story number.
- Every nesting level after that adds exactly **two digits** (01–99).
- Maximum 99 siblings at any level below a story.

---

## Filename Format

Files with their own file (basic or extended) include a short summary slug appended to the ID:

```
s01-design-file-structure.md
s01-design-file-structure/        ← extended form (dir)
  README.md
  s01t01-define-task-forms.md
  s01t01-define-task-forms/       ← nested extended form
    README.md
    s01t0101-first-subtask.md
    s01t0102-second-subtask.md
  s01t02-write-cli-spec.md
```

**Rules:**
- Slug is only required for basic and extended tasks (those with their own file)
- Inline tasks have an ID but no slug and no file
- Slug is kebab-cased, max 5 words
- Derived automatically from the task title, or set explicitly via `--slug`
- The slug is cosmetic — tasks are always addressed by ID alone (`s01`, `s01t02`, `s01t0102`)
- When referencing a task in commands, both forms are accepted:
  - `s01t01` — ID only
  - `s01t01-define-task-forms` — full filename stem (slug ignored for lookup)

---

## File Structure

### Basic task

```
planning/
  s01-design-file-structure.md
```

### Basic task with inline subtasks

```
planning/
  s01-design-file-structure.md    ← contains ## Subtasks bullet list
```

### Extended task (recursive)

```
planning/
  s01-design-file-structure/
    README.md                     ← task description + list of subtask links
    s01t01-define-task-forms.md   ← basic subtask
    s01t02-write-cli-spec/        ← extended subtask
      README.md
      s01t0201-draft-commands.md
      s01t0202-write-tests.md
```

Root-level stories live directly under `planning/`. Archived tasks move to `planning/archive/`.

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

- [ ] s01t01: pending subtask
- [~] s01t02: in-progress subtask
- [x] s01t03: finished subtask
```

**`## Props`** — required `Status:`, optional `Depends:`

| Status value | Meaning |
|---|---|
| `pending` | not started |
| `in-progress` | being worked on |
| `done` | finished |

**`## Subtasks`** — present in the basic form when it has inline subtasks. Each line is a checkbox entry with the subtask ID and title.

For the **extended** form, `README.md` lists subtasks as links:

```
## Subtasks

- [ ] [s01t01](s01t01-define-task-forms.md): Define task forms
- [~] [s01t02](s01t02-write-cli-spec/): Write CLI spec
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
tasker new <title>

# Add a root-level story with explicit slug and description
tasker new <title> --slug <slug> --details <description>

# Add a simple inline subtask under any parent
tasker add <parent-id> <title>

# Add a subtask with details — auto-upgrades parent to extended form
tasker add <parent-id> <title> --details <description>

# Add with explicit slug (e.g. when created by AI)
tasker add <parent-id> <title> --details <description> --slug <slug>
```

### Update task status

```bash
# Mark in-progress
tasker start <task-id>

# Mark done (fails if task has open subtasks)
tasker done <task-id>

# Force close even with open subtasks
tasker done <task-id> --force-close
```

### List and query

```bash
# List all root stories with status summary
tasker list

# List subtasks of any task
tasker list <task-id>

# Tasks with all dependencies satisfied
tasker list --ready

# Tasks blocked by unfinished dependencies
tasker list --blocked
```

### Archive

```bash
# Move root story to planning/archive/
tasker archive <task-id>
```

Only root stories can be archived. Archiving a non-root task is an error.

> **TBD:** Archiving of mid-tree tasks may be supported in the future.

---

## Examples

```bash
# Create a root story
tasker new "Design file structure"
# → planning/s01-design-file-structure.md  (Status: pending)

# Create with description
tasker new "Design file structure" --details "Define how tasks are stored on disk"
# → planning/s01-design-file-structure.md  (description included)

# Add an inline subtask (no file created, gets an ID in ## Subtasks list)
tasker add s01 "Define task forms"
# → - [ ] s01t01: Define task forms  (in planning/s01-design-file-structure.md ## Subtasks)

# Add a subtask with details — auto-upgrades parent to extended form
tasker add s01 "Write CLI spec" --details "Cover all commands and options"
# → planning/s01-design-file-structure/README.md  (parent upgraded)
# → planning/s01-design-file-structure/s01t02-write-cli-spec.md

# Add a subtask under a subtask — two digits appended
tasker add s01t02 "Draft commands" --details "List every command with args"
# → planning/s01-design-file-structure/s01t02-write-cli-spec/README.md  (parent upgraded)
# → planning/s01-design-file-structure/s01t02-write-cli-spec/s01t0201-draft-commands.md

# AI-created task with explicit slug
tasker add s01 "Implement command parsing" --details "..." --slug "impl-cmd-parsing"
# → planning/s01-design-file-structure/s01t03-impl-cmd-parsing.md

# Reference by ID or full name — both work
tasker start s01t02
tasker start s01t02-write-cli-spec

# Close workflow
tasker done s01t0201
tasker done s01t02
# Error: s01t02 has open subtasks. Use --force-close to override.

tasker done s01t01
tasker done s01
```
