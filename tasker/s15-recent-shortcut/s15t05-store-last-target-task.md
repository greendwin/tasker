---
id: s15t05
status: pending
---

# Store last target task

Remember task id on following operations:
- new
- add
- move
- edit
- unarchive

Note: remember when task is referenced by *direct* reference.

```bash
# q := s01t02
tasker edit s01t02 -d "test"
```

Accessing using `q` NEVER updates reference

TBD: should we update `q` on ANY direct reference usage?
why `tasker start s01t02` does not reset `q` to `s01t02`?
HOw to reference its parent in this case?