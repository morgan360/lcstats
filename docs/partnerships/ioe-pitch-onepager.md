# One-pager and demo script — Institute of Education

**Hold both until the meeting is agreed.** Neither goes in the first email.

Re-verify every number on the day (see `../../` plan, Verification). Figures below are from
production on 2026-08-17.

---

# Part 1 — The one-pager

Print it. One side of one page. Bring three copies: her, Roantree, and one to leave behind.

---

## NumScoil — automatic marking for Leaving Certificate Maths

**Built and maintained by [Company], in partnership with Morgan McKnight, a practising
Leaving Certificate Higher Level maths teacher, who authors the content.**

### What it does

A student types a maths answer. NumScoil marks it against the criteria of the official
marking scheme, awards partial credit, and explains the mark — in seconds, at any hour, for
every student at once.

It compares the mathematics directly, so `1/2`, `0.5` and `2/4` are the same answer and an
algebraically equivalent rearrangement is correct. AI is used for the parts that need
judgement — written reasoning, and reading handwriting — not for the arithmetic.

### What a student gets

- **516 practice questions** across 21 topics and 199 sections of the Higher Level course
  — practice to work through, not an archive to browse
- Worked solutions in steps, and hints that cost marks to use, so the incentive matches the
  exam
- **Photograph your handwritten working.** Scan a QR code, shoot the page on your phone, and
  have the method itself read and commented on — because maths is not typed
- 198 flashcards with spaced repetition, and full past papers under timed conditions

### What a teacher gets

- Assign homework to a class by topic, section or question, and see who has done it
- Per-student progress: attempts, marks, and where they are stuck
- Marking that has already happened by the time the class meets

### What the Institute gets

- A digital platform without building or maintaining one
- Your name on it, or co-branded with a share of the revenue — your choice
- Something the grinds cannot do alone: every student's homework marked, individually, every
  night
- Runs alongside Moodle today; integrates into it if a pilot works

### Who owns what

The software and content are owned and maintained by us. The Institute licenses it. Anything
commissioned specifically for the Institute belongs to the Institute. No student data is sold
or used to train models.

### Where it stands

Higher Level Maths is complete and in use. Ordinary Level is next, then further subjects.
The Institute would be the first partner of scale — which is reflected in the terms.

**Pricing on request** — it depends on which model suits you.

[phone] · [email] · numscoil.ie

---

# Part 2 — Demo script (12 minutes)

Strongest first. If she stops you at minute four to talk terms, you have won — stop
demoing.

**Setup:** own laptop, phone hotspot, two browser windows already logged in (student and
teacher), the exact questions pre-located. Never trust guest wifi. Never navigate from the
homepage while they watch.

### 1. Marking against the scheme (3 min) — *the whole pitch*

Open a Higher Level question. Type an answer that is **wrong but close** — right method,
arithmetic slip. Let it mark and explain.

> "That's marked against the marking scheme criteria, with partial credit. Every student,
> every question, immediately."

She examined for the SEC. This is the moment she decides whether the rest is worth her time.
Do not rush it and do not talk over it while it works.

### 2. The equivalent-answers problem (1 min)

Same question. Type `1/2`. Then `0.5`. Then `2/4`. All accepted.

> "Any maths teacher's first test of a system like this is whether it's pedantic about form.
> It isn't."

Small, and exactly what Roantree will probe within a minute of seeing it. Naming that you
know it is the first thing tested earns credibility with him specifically.

### 3. Photograph your working (3 min) — *the differentiator*

Show the QR code on screen, scan it with your own phone in front of them, photograph a
handwritten solution, and let it read and comment.

> "Maths isn't typed. The student scans that, shoots the page, and the method itself gets
> read — the same thing you'd look at over their shoulder."

**Scan the QR code in the room.** Doing it live is the whole point: it proves there is no
app to install, no account on the phone, no friction — which is what makes the difference
between a feature that exists and one students actually use.

Nothing else in the Irish market does this. Two safeguards: have a **pre-photographed
fallback image** ready in case the upload is slow, and note the upload link expires after 15
minutes, so generate it fresh rather than reusing one from the practice run. A stall here is
worse than skipping the segment.

*Verified live for students on production (`WORK_PHOTO_STAFF_ONLY=False`) — it was
staff-gated during the trial, so confirm the flag before demoing.*

### 4. Hints and solutions, priced in marks (1 min)

Show the hint (−20%) and the full solution (−50%), and that solutions unlock after two
attempts.

> "A student can always get unstuck, but never for free. It mirrors how you'd scaffold in a
> grind."

This is a pedagogy point, not a feature. It tells them a teacher designed it.

### 5. The teacher side (3 min) — *what she actually buys*

Switch to the teacher window. Create a class, assign homework, show the progress view.

> "This is the part for your teachers. The marking is done before the class meets, and you
> can see who didn't attempt it."

Students want the practice; a principal buys visibility and staff time. Spend the full three
minutes here — it is the second most important segment after (1).

### 6. Proof by Induction (1 min) — *proof of momentum*

> "These nine went in this month — three sections, twenty-seven parts, with solutions. That's
> the rate content is added at."

Answers "will this be maintained?" without being asked.

### 7. Stop

**Do not show:** Physics (one topic on production), the Django admin, the InfoBot unless
asked, anything half-built, or the user numbers.

Close with a question, not a summary:

> "Does this look like something your students would use — and would you rather it carried
> your name, or ours alongside yours?"

That question makes the next conversation about *structure* rather than *whether*.

---

## Handling the three hard questions

**"How is this different from Studyclix?"**
> "Studyclix shows the student the marking scheme. We mark the student's own attempt against
> it. One is a library; this is a marker."

Do not disparage them — 250,000 students use it and she knows that. Concede the archive, own
the marking.

**"We already have Moodle."**
> "It runs alongside Moodle now — students sign in with Google. If a pilot works, the path is
> LTI, so it sits inside Moodle and marks flow to your gradebook. I'd rather prove the
> marking is worth having before asking you to integrate anything."

Be straight that LTI is not built. Offering to prove value first is a stronger position than
overclaiming.

**"Is this AI? Can we trust it to mark our students?"**
> "The arithmetic and algebra aren't AI — it compares the mathematics directly, so equivalent
> forms are accepted and the result is the same every time. AI does two things: it reads
> handwriting, and it judges written reasoning where a marking scheme would want a human to
> judge it. And the student always sees the worked solution, so they can check the mark
> against it."

Do not oversell autonomy. The strongest position is that the deterministic parts are
deterministic and the student can always see the reasoning. If she pushes on error rates, say
plainly that there is no published accuracy study and offer to make the pilot produce one.

**"Where does student data go?"**
> "Answers go to OpenAI for the marking steps that need it — they're a sub-processor, and
> that goes in the agreement. Photographs of working are stored privately, served only to the
> student who took them and to staff, and deleted after 90 days. Nothing is sold and nothing
> trains a model."

Say this before she has to ask twice. These are minors, and volunteering it reads as
competence rather than concession.

⚠️ **Confirm the 90-day purge actually runs before stating it.** `WORK_PHOTO_RETENTION_DAYS`
defaults to 90 and `students/management/commands/purge_work_photos.py` implements it, but
production holds only 9 submissions and none is yet older than 90 days — so the deletion has
never actually had to happen. PythonAnywhere scheduled tasks have been found silently broken
before. Check the task exists and its output is recent; otherwise this is a policy rather
than a practice, and it will be written into a DPA as a commitment.

**"Whose exam papers are those?"**
> "A licensing request is with the SEC and is being processed. The practice questions are
> separate from that, and the platform stands on those regardless of how the SEC answers."

Only usable once the letter has gone. If it has not, say the request is being prepared — do
not embellish.

⚠️ **Do not claim all 516 practice questions are your original work.** The database cannot
support it (202 flagged one way, 314 the other, and the flag's meaning is documented in
opposite directions in the model and in the `extract-question` skill). Quote only the number
you can personally stand over. Roantree is a textbook author and O'Toole has written 37 —
provenance is a subject they take seriously and will ask about precisely.

## What she will ask that has no good answer yet

Anticipate these and answer honestly. A confident "not yet, here's the plan" costs far less
than a bluff that unravels:

- **"How many students use it?"** — Early. Trialled in a school setting and revised on that
  basis. The Institute would be first at scale.
- **"What are the results?"** — No outcome study yet. Offer to make the pilot produce one:
  their cohort, measured, published jointly. Turns the weakness into the reason to pilot.
- **"What if you're not available?"** — [Company] builds, hosts and maintains it; support
  does not depend on one person.
- **"Can we see it ourselves first?"** — Offer a supervised second session with the maths
  department rather than logins. Access after the demo, not before.
