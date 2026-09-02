# Homework Check — where we are

Handover note, written 2026-09-02. Read this before changing anything in
`homework_check/` or `hw_solutions/`.

## What it does

A teacher opens `/homework-check/new/`, picks a class and a student, names the
exercise, chooses which solutions PDF to mark against and which exercise inside
it, then uploads up to 16 photos of the student's copy. The photos are analysed
in batches of four against the relevant solution pages, and the result is a
one-page printable sheet: questions attempted, what went wrong, the correct
answers, and an Excellent/Good/Fair/Poor box the teacher can override.

Approved plan: `~/.claude/plans/could-we-create-a-zippy-dusk.md`.

## Current state — live and working

| | local | production |
|---|---|---|
| Initial feature | `2a9d5a08` | `41fce299` |
| Exercise picker | `3d1d22b9` | `2b316eef` |
| Token ceiling + failed-batch fixes | `896a7767` | `1740279f` |
| Rendered maths preview | `3fd3915e` | `8b324bd6` |

Migrations applied on prod: `hw_solutions.0001`–`0003`, `homework_check.0001`.
Nothing pending.

Test suite: **210 tests, 1 failure**, and that one failure is
`reports.tests.ActivityServiceTests.test_get_activity_by_day_counts_sources`,
which is pre-existing and unrelated — see *Known bugs* below. Everything in
`homework_check` and `hw_solutions` passes (74 tests).

**Real handwriting now works.** This was the outstanding unknown — everything
before today had been validated on rendered text, not a real student's copy.
On 2026-09-02 a real 8-photo copy was marked against the real Active Maths
solutions PDF and produced 13 questions at `confidence=medium`,
`readable=True`. The hard part is proven.

## What changed today

### 1. Pick the exercise by name (`3d1d22b9`)

Was: a free-text "Pages (optional)" box, and leaving it blank sent the whole
84-page chapter to the model with *every* batch of photos.

Now: `hw_solutions/services.py` indexes each PDF once by reading the running
header, caches the result in `HWSolutionSection`, and the teacher picks
"Exercise 1.3" from a dropdown. Falls back to a hand-typed range when a PDF has
no headings. `python manage.py index_hw_solutions [--force] [--id N]` re-indexes;
the view also indexes on demand, so a PDF uploaded through the admin needs no
extra step.

Two bugs that only showed up against a real book, both now fixed and tested:

- **`Revision Exercise` printed above the chapter number `07` was read as
  "Exercise 07".** The regex searched the page as one string and ran through the
  line break. It named a section that does not exist and pointed at fourteen
  wrong pages. Headings are now matched one line at a time.
- **Named back-of-chapter sections were invisible.** `Revision Exercise` and
  `Exam Questions` produced no label at all, hiding 20 of 73 pages — and those
  are as likely to be set for homework as the numbered exercises.

What it detects in the live Algebra chapter (`HWSolution` id 1, 84 pages):

| Section | Pages | |
|---|---|---|
| Exercise 1.1 | 2–12 | 11pp |
| Exercise 1.2 | 13–16 | 4pp |
| Exercise 1.3 | 17–21 | 5pp |
| Exercise 1.4 | 22–26 | 5pp |
| Exercise 1.5 | 27–35 | 9pp |
| Exercise 1.6 | 36–50 | **15pp** |
| Exercise 1.7 | 51–54 | 4pp |
| Revision Exercises | 55–83 | **29pp** |

### 2. Token ceiling and silently dropped photos (`896a7767`)

Both found by marking a real copy on production, and both were live.

**The output ceiling includes reasoning tokens.** `_vision_completion`
(`exam_papers/services/vision_grading.py:52`) passes
`max(max_tokens, REASONING_TOKEN_BUDGET)` as `max_completion_tokens`, and on
`gpt-5.5` that single budget covers the model thinking *and* the JSON it
returns. At `MAX_TOKENS = 3000` the effective ceiling was 4000, and real batches
of thirteen questions were using 3715–3910 of it. The batches that tipped over
came back HTTP 200 with an **empty string** where the JSON should be, which the
teacher was shown as *"That batch couldn't be read. Check the photos are flat…"*
— a token ceiling wearing the costume of a bad photograph. `MAX_TOKENS` is now
9000.

The empty body is now its own exception, `check_analysis.EmptyResponse`, and the
handler logs `finish_reason` and the token counts. Worth knowing: the cause above
is inferred from strong evidence (200 OK, empty content, successful calls landing
within ~90 tokens of the ceiling) rather than directly observed — `finish_reason`
was not being logged at the time. The new logging will confirm it if it recurs.
**If it does recur, the answer is more headroom, never better photographs.**

**A failed batch was silently dropped and counted as complete.** This one is
worse. `pending_photos()` retries only photos with status `PENDING`, and
`progress()` counts anything *not* `PENDING` as done. A failed batch was marked
`FAILED`, so it was never retried *and* it counted towards completion. The log
shows exactly what that looked like:

```
10:46:52  Homework check 1 failed during analysis
10:47:10  Completed homework check 1: 13 question(s), rating=fair
```

Eighteen seconds after losing four of eight pages, that check printed a "fair"
rating on half a student's homework with nothing on the sheet saying so.
`derive_rating`'s readable/confidence guards could not catch it, because they
inspect chunks and a batch that died leaves none.

Now: a retryable failure leaves its photos `PENDING`, so pressing the button
again picks up the same batch, and `assemble(chunks, failed_photos=n)` withholds
the rating entirely when any page went unanalysed, with the reason *"N page(s)
could not be analysed, so this covers only part of the work"*.

**Any new failure path must pick one of those two behaviours.** Leaving a photo
in a state that is neither retried nor flagged is how this happened.

A stalled progress bar is now the honest signal that something failed. It is not
a bug.

### 3. Rendered maths on the review page (`3fd3915e`)

The model wraps every expression in `$...$`, which is what makes the printed
sheet readable. But on the review page the comments sit in `<textarea>`s, and a
textarea can only ever show plain text — so the teacher checking the work read
`$-q^2$, not $-2q$` while the student's sheet said the same thing in proper
maths. The Theirs/Correct lines directly above render fine, which is what made
it look like a fault in the comment.

Each box now has a rendered copy above it, updated as you type. Applies to the
question comments, the closing note and the teacher's own note.

The model's formatting rules were deliberately left alone: asking for less LaTeX
would fix the teacher's view by degrading the sheet that actually gets handed to
the student.

## Decisions already made — do not re-litigate

- **The prompt deliberately states the correct answer**, inverting the strictest
  rule in `exam_papers/services/work_analysis.py`. Safe because the sheet is
  handed over *after* the teacher reads it, and the same PDF is already
  downloadable by students from the Downloads menu. Do not "fix" it to match.
- **No marks.** A four-band rating instead, computed in code from verdict
  counts, and withheld whenever anything is doubtful.
- **A slip is worth half, not full** (`VERDICT_CREDIT`). Counting slips as
  correct rated a student who got every answer wrong through sign errors as
  "Excellent".
- **Batches of four photos, browser-driven.** Sixteen in one call runs past
  `OPENAI_VISION_TIMEOUT` and holds a web worker; there is no queue in this
  project. One photo at a time was considered and rejected: the solution pages
  are re-sent with every call, so 8 photos singly is 88 page-images instead of
  22 — four times the spend and four times the wait.
- **Nothing writes to `StudentSessionRecord`.** The reports link is a link only.
- **The class picker shows the teacher's own classes**, not every class, even
  for a superuser. `?all=1` restores the full list. `_owned_classes` still backs
  the permission checks and stays permissive; `_pickable_classes` is what the
  dropdowns use.

## Open decisions

**`HOMEWORK_CHECK_MAX_SOLUTION_PAGES` is 12, and this needs a number.** The
solution pages go up with every batch, so a long exercise is the expensive case.
At 12, Exercise 1.6 (15pp) and Revision Exercises (29pp) are both refused with
"pick a narrower range" — and Exercise 1.6 is an ordinary homework set. 29 pages
arguably *should* be refused. It is an env var, so it can be changed on prod in
seconds with no redeploy.

The alternative, which removes the pressure entirely but is real work: send the
solution pages **once per check** rather than once per batch.

## Known bugs, not yet fixed

- **`reports` activity-by-day is broken in production.** The MySQL timezone
  tables are not loaded, so `CONVERT_TZ('…','UTC','Europe/Dublin')` returns
  `NULL`. With `USE_TZ = True` Django compiles `TruncDate` to `CONVERT_TZ`, so
  `reports/services.py:76` buckets every activity row under a `None` date. This
  is what makes that one test fail, and it is not test-only. Fix is either
  loading the tz tables into MySQL or bucketing in Python.
- **Checks 1 and 2 in production should be deleted.** Both were assembled from
  partial photo sets before the fix above, so their ratings describe a fraction
  of the work.

## Still to do

- Add the `purge_homework_checks` daily task by hand in the PythonAnywhere web
  UI. There is no `crontab` and no SSH or API route to scheduled tasks, so this
  can never be done from a session.
- Check the scheduled tasks that already exist actually ran — a task that never
  runs looks identical to one with nothing to do.

## Deploying — read this, it changed today

**Production can no longer `git pull`.** `git fetch origin main` on the server
fails with `could not read Username for 'https://github.com'`. There is no
credential helper and no `~/.git-credentials`, and prod's `~/.ssh/id_rsa` is not
registered with GitHub (`ssh -T git@github.com` → `Permission denied
(publickey)`). Neither remote works. The procedure in
`docs/PYTHONANYWHERE_DEPLOYMENT.md` and in the deploy memory is out of date.

What works, and what was used for all three deploys today:

```bash
# 1. commit and push locally as normal, then:
COPYFILE_DISABLE=1 tar czf - <named file> <named file> ... \
  | ssh ssh.eu.pythonanywhere.com 'cd ~/lcstats && tar xzf -'

# 2. on the server
cd ~/lcstats
./venv/bin/python manage.py migrate <app>     # only if there are migrations
git add <the same named files> && git commit -m "Deploy: … (targeted copy of <sha>)"
touch /var/www/www_numscoil_ie_wsgi.py
```

Before overwriting anything, **check prod's copy matches the committed
baseline** — `md5sum` on the server against `git show <sha>:<file> | md5`
locally. A mismatch means prod carries an edit the copy would destroy.

Name individual files, never a directory. Production's `main` has diverged from
origin on purpose and carries migrations that exist nowhere else; a path-scoped
operation over a directory deletes them. Expected `git status --porcelain -uno`
on prod is exactly two modified files —
`interactive_lessons/migrations/0024_merge_20260116_1736.py` and
`scripts/daily_logout.sh`. Anything else is a surprise worth reading first.

The venv is `~/lcstats/venv` and prod is **Python 3.10**, older than a typical
local 3.12, so 3.11+ syntax will import locally and break on the server.
Template-only changes need no `collectstatic`; anything touching `static/`
does.

Fixing this properly means adding prod's `~/.ssh/id_rsa.pub` to GitHub as a
deploy key and switching the remote to SSH. That is a GitHub UI job.

## Traps worth not rediscovering

- `gpt-5.4-mini` (the configured `OPENAI_CHAT_MODEL`) **rejects `max_tokens`**
  but accepts `temperature`. Any new chat call needs the `LEGACY_PARAM_MODELS`
  split that `_vision_completion` makes. The vision model is separately
  configured and is currently `gpt-5.5`.
- A field named `check` on a model collides with Django's `Model.check()` and is
  refused by system checks. The FK is `hw_check`.
- Photos live under `PRIVATE_MEDIA_ROOT`, not `MEDIA_ROOT`: on PythonAnywhere
  `/media/` is a static mapping served outside Django and cannot be permission
  checked, and these are photographs of a named child's work.
- The prod reload takes ~40s, during which the path 404s. That is not a broken
  deploy.

## Where things live

| | |
|---|---|
| Vision call and prompt | `homework_check/services/check_analysis.py` |
| Batch driver, retry, finalise | `homework_check/services/runner.py` |
| Rating, merging, withholding | `homework_check/services/assembly.py` |
| Closing summary (text-only call) | `homework_check/services/summarise.py` |
| Exercise detection | `hw_solutions/services.py` |
| Review page | `homework_check/templates/homework_check/check_detail.html` |
| Printed sheet | `homework_check/templates/homework_check/report_print.html` |
| Offline probe (no phone needed) | `manage.py check_homework_photos --pdf … --photos …` |
