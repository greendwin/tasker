---
id: s11
status: pending
---

# Tasks archivation

add 'archive' command that moves complete task to 'planning/archive'

## Subtasks

- [x] s11t01: Make sure that task is done
- [x] s11t02: Support --force option (mark tasks as cancelled)
- [ ] s11t03: TBD: reference tasks in archive
- [ ] s11t04: TBD: unarchive task
- [ ] s11t05: TBD: unarchive by adding to a task (maybe we should unarchive root task first)
- [ ] s11t06: Add 'unarchive' command
- [x] s11t07: 'new' command must count archived task IDs on creation, so 'unarchive' will never collide
- [x] s11t08: Actions on archived task must report that task is archived; note: dont load archived tasks, store ids of archived root tasks, its enought
