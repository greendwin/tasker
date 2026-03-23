---
id: s02
status: pending
---

# Tasks forkflow start-stop-done

## Subtasks

- [x] s02t01: update status in story prop
- [x] s02t04: update bullet list tasks status
- [x] s02t05: update parent task status automatically
- [x] s02t08: Show story ref on task creation
- [x] s02t09: All messages must start in the same case
- [x] s02t06: Add 'done' command
- [x] s02t10: Its ok if parent in-progress task is tryed to be started (idempotent operation) - show list of in-progress tasks, but still show warning about managed status
- [x] s02t11: Support --force option for 'done' command -- force stop all nested tasks
- [x] s02t07: ~~Tell current subtask status when trying to edit subtask with status~~
- [x] s02t12: ~~TBD: strikethrough task id in bullet list~~
- [x] s02t33: ~~TBD: sort tasks - done / in-progress / pending~~
- [ ] s02t02: support all start/stop/done states
- [ ] s02t03: add 'stop' command
- [x] s02t34: Add 'cancel' command - strikethrough title for such commands; add CANCELLED status
- [x] s02t35: Print forcibly closed tasks on 'done --force'; also add them to 'json-output'
- [ ] s02t36: Check all commands: trying to change status when it already in that status is not an error
