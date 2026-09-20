# Study Plans: the nightly run

Study plans need one scheduled job. Without it a checkpoint never opens by
itself, nothing is carried forward, and a student who finishes their work sees
no change until a teacher presses **Check progress now**.

There is no background queue in this project, so cron is the whole mechanism.

## The command

```bash
python manage.py run_study_plans
```

What it does, per active plan, in order:

1. Marks items whose evidence says they are done (only work dated on or after
   the item became available counts).
2. Opens the checkpoint of any topic whose practice is ~80% finished.
3. Marks any checkpoint the student has finished sitting.
4. On a pass: records the mastery and retires that topic's leftover practice.
   On a fail: adds more work and sets a fresh checkpoint on unseen parts.
5. Carries unfinished work into the current week, up to three times, then tells
   the teacher instead.

It is safe to run twice. Work already counted is not counted again, a decided
checkpoint is never re-marked, and an item already moved is left alone. It never
deletes anything and never moves an item a teacher chose by hand.

## Options

| Flag | What it does |
|---|---|
| `--dry-run` | Reports what would change and writes nothing |
| `--plan <id>` | One plan only |
| `--student <username>` | One student's plans only |
| `--date YYYY-MM-DD` | Treats that date as today (for testing) |

Always try `--dry-run` first after changing anything:

```bash
python manage.py run_study_plans --dry-run
```

## Scheduling on PythonAnywhere

Tasks tab → **Create a new scheduled task**, daily, a little after midnight
local time so a full day's work is counted:

```
cd /home/<user>/lcstats && ./venv/bin/python manage.py run_study_plans
```

## Scheduling with cron

```cron
15 1 * * * cd /path/to/lcstats && /path/to/venv/bin/python manage.py run_study_plans >> /var/log/study_plans.log 2>&1
```

Run it alongside the other daily jobs (see `DAILY_REPORT_USAGE.md`). Order does
not matter; they do not touch the same rows.

## Checking it is working

```bash
python manage.py run_study_plans --dry-run
```

should report the number of active plans it can see. If that number is 0 while
plans exist, they are `draft`, `archived`, `completed`, or `is_locked` — only
active, unlocked plans are touched.

Students can always force a check themselves from **Check my progress** on their
plan page, and teachers from **Check progress now** on the plan. Those exist so
a tick appears the same evening the work is done; the nightly run is what keeps
things moving when nobody presses anything.
