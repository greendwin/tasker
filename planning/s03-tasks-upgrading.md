---
id: s03
status: pending
---

# Tasks upgrading

## Subtasks

- [ ] s03t01: upgrade on adding detailed task
- [ ] s03t02: upgrade on adding subtask to inline task
- [ ] s03t03: add 'edit' command that changed --details (note: all fields, title and etc must be editable in future, see separate story)
- [ ] s03t04: Upgrade when adding a subtask to inline task
- [x] s03t05: When flushing tasks -- check for extended flag change (task can be upgraded from simple to extended), we need to remove old .md file and create a directory on save
- [x] s03t06: Refactor basic and extended task types - use extended bool flag
- [x] s03t07: Extended flag must be recalculated the same as status (on load and on parents update) - it's criteria is that task has non-inline subtaks, BUT it could be loaded as extended, so it should not convert it back to basic task
- [ ] s03t08: Need to upgrade recursively (support deep nesting)
- [ ] s03t09: Convert inline task to file task by adding subtask
- [x] s03t10: Get rid of InlineTask type - it should be an attribute like extended
- [ ] s03t11: Task nested path is dependant on parents extended flag, make sure that it does not miss prev file
- [x] ~~s03t12: In unified Task object slug still should be created, but it's ref should not include it until it upgraded~~
- [x] s03t13: Support --details and --slug to 'add' command, support non-inline subtask
- [ ] s03t14: BUG: Error: Cannot resolve task reference 's09t0101'
- [ ] s03t15: BUG: 3-rd layer tasks are REMOVED on tasks validation (on idempotent operation!)
