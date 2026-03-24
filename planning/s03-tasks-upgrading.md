---
id: s03
status: pending
---

# Tasks upgrading

## Subtasks

- [ ] s03t01: upgrade on adding detailed task
- [ ] s03t02: upgrade on adding subtask to inline task
- [ ] s03t03: add 'update' command that changed --details (note: all fields, title and etc must be editable in future, see separate story)
- [ ] s03t04: Upgrade when adding a subtask to inline task
- [ ] s03t05: Support 'upgrade' method in TaskRepo: change type to ExtendedTask and remove old file on flush
- [x] s03t06: Refactor basic and extended task types - use extended bool flag
- [x] s03t07: Extended flag must be recalculated the same as status (on load and on parents update) - it's criteria is that task has non-inline subtaks, BUT it could be loaded as extended, so it should not convert it back to basic task
