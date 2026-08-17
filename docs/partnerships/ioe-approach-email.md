# Approach email — Institute of Education

**Objective: one 20-minute meeting.** Not a sale, not a price, not a login.

Replace `[Company]` throughout with the software company's name, and only after they have
agreed to be named (see the plan's conditions).

---

## Routing — do this before sending

There is no published email address for individual staff and no partnership route. The site
lists only `info@instituteofeducation.ie` and **01 661 3511**.

1. **Phone 01 661 3511.** Ask for the correct address for a commercial proposal to the
   Principal. Say what it is in one sentence — a platform that marks Leaving Cert maths
   answers against the marking scheme — and ask whether it should go to her directly or to
   someone else.
2. If they will not give an address, send to `info@` with **"For the attention of Yvonne
   O'Toole, Principal"** as the first line of the body.
3. Send the short version below as a LinkedIn message the same day. Two channels, one day,
   is persistence; two channels a week apart looks like a mailing list.

Phoning first matters more than any sentence in the email — it turns a cold email into an
expected one. Ask the receptionist's name and reference the call in the subject line.

**Timing:** send Tuesday–Thursday morning. Avoid Monday (timetable chaos in week one) and
Friday afternoon.

---

## The email

**Subject:** Marking LC maths against the marking scheme — 20 minutes?

*(If you phoned first: `Following my call today — marking LC maths against the marking scheme`)*

---

Dear Ms O'Toole,

You examined for the State Examinations Commission, so you will judge this faster than most:
NumScoil marks a student's maths answer against the official marking scheme and explains the
mark in seconds, partial credit included.

NumScoil is built and maintained by [Company] in partnership with me. I teach Leaving
Certificate Higher Level maths and give grinds, and I author the content — 516 practice
questions across 21 topics of the Higher Level course, with hints, worked solutions, and a
teacher dashboard for setting and tracking homework. It has been trialled with real students
and revised on the strength of how they used it.

I would like to propose that the Institute offer it to its students, either carrying your
own name or co-branded with a share of the revenue. We own, host and maintain the platform,
so the Institute would have one without building it.

Aidan Roantree is the right person to say whether the maths meets your standard, and I would
welcome his verdict. Could I show it to you both, for twenty minutes, on Leeson Street?

I know term starts next week. That is precisely why I am writing now.

Kind regards,

Morgan McKnight
[phone] · [email] · numscoil.ie

---

*198 words. Do not attach anything.*

---

## Why each part is there

- **First line names her SEC examining.** It is specific, it is flattering without being
  fawning, and it tells her the product is about marking rather than content delivery —
  which is the part she is uniquely equipped to assess.
- **"Partial credit included"** is the detail that separates this from a right/wrong quiz.
  An examiner will notice.
- **[Company] first, then Morgan.** The vendor is a software company; Morgan is the subject
  authority. Present tense throughout — nothing claims the company was there from the start.
- **516 practice questions across 21 topics** is the one number. It is verifiable on
  production and large enough to show seriousness.

  ⚠️ **Do not write "516 original questions" unless you can personally stand over that.**
  The database cannot support it: `is_copyrighted` is True on 202 and False on 314, and the
  field's meaning is contradictory in the codebase — the model's help text says True means
  "copyrighted, e.g. from published exam papers" while the `extract-question` skill says True
  means "Original NumScoil content". You authored these, so you know the real provenance;
  insert the number you can defend, or leave the adjective out. An overclaim about
  originality to a textbook author who examined for the SEC is the worst possible place to
  be caught out.
- **Both models offered in one sentence.** Let her pick the one that suits her governance
  rather than guessing which it is.
- **Roantree by name** routes the email to whoever will actually judge the maths, shows you
  know the school, and flatters him via her. Offering his verdict rather than his login
  keeps the first impression supervised.
- **Naming the short notice** turns the timing from sloppy into deliberate.
- **No price, no attachment.** A price gives her a reason to decide without meeting you. An
  attachment gets it forwarded and filtered.

## LinkedIn version (under 300 characters)

> Ms O'Toole — I teach LC Higher Level maths. NumScoil marks a student's answer against the
> official marking scheme and explains the mark in seconds. I'd like to propose the
> Institute offer it to students, co-branded or under your own name. Could I show you and
> Aidan Roantree 20 minutes? — Morgan McKnight

## If there is no reply

**One follow-up, ten days later. One only.**

> Dear Ms O'Toole,
>
> Following up briefly on my note of [date] about NumScoil, which marks Leaving Cert maths
> answers against the official marking scheme.
>
> If it is not of interest, do say and I will not chase it. If the timing is simply wrong
> with term starting, I am happy to come back in October.
>
> Kind regards,
> Morgan McKnight

Giving her a costless way to say no makes a reply far more likely, and a "not now, try
October" is a good outcome rather than a failure.

**If she declines or does not reply after the follow-up:** Bruce College in Cork is also
Dukes-owned and a smaller, faster decision. The Dublin Academy of Education is independent
and already sells on-demand online courses. Neither is a consolation prize.

## Answers to have ready

She may reply with a question rather than a meeting. Short answers, no essays:

- **"How is this different from Studyclix?"** Studyclix shows you the marking scheme.
  NumScoil marks the student's own attempt against it and explains the mark.
- **"We already use Moodle."** It runs alongside Moodle today. If a pilot works, the
  integration path is LTI so it sits inside Moodle with grades flowing to your gradebook.
  *(Be straight that this is not built yet.)*
- **"Are you using our exam papers / SEC material?"** A licensing request is with the SEC
  and being processed, and the practice questions are separate from it. *(Only say this once
  the letter has actually gone — and see the provenance warning above before characterising
  the practice questions.)*
- **"How many schools use it?"** It has been trialled in a school setting and revised on
  that basis; this is early and the Institute would be the first partner of scale — which
  is why the terms on offer are better than they will be later.
- **"Send me pricing."** Suggest the twenty minutes first, since the right structure depends
  on whether they want it under their own name or co-branded. Do not send a rate card.
