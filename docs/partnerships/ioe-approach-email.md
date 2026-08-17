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

**Subject:** An online maths tutor for your Leaving Cert students — 20 minutes?

*(If you phoned first: `Following my call today — an online maths tutor for your LC students`)*

---

Dear Ms O'Toole,

I teach Leaving Certificate Higher Level Maths, and our company has built a platform we would
like to offer to the Institute for its students.

NumScoil is an online tutor for Leaving Certificate Higher Level Maths. Students work through
practice questions covering the full course — 516 of them across 21 topics — with hints,
worked solutions in steps, flashcards, and past papers under timed conditions. Teachers can
assign work to a class or to individuals and monitor their progress.

What distinguishes it from a revision website is that it marks students' work in real time. A
student types an answer and NumScoil marks it against the criteria of the official marking
scheme, awards partial credit, and explains the marking. It compares the mathematics
directly, so equivalent forms are accepted; AI is used for the parts that need judgement —
written reasoning, graphs and drawings.

Work done on paper can be submitted too. Students scan a QR code, photograph their working
with their phone, and the platform returns a reasoned analysis of the method, with an
estimated mark against the official scheme on exam questions. Where the writing cannot be
read with confidence it declines to put a mark on it rather than guess.

It is built and maintained by us, and has been trialled with real students and revised on the
strength of their feedback.

Our proposal is that the Institute offer it, either under your own name or co-branded with a
share of the revenue. We would own, host and maintain it, so you would carry none of the
burden of hosting, maintenance or updates.

I would be glad to demonstrate it in Leeson Street — twenty minutes would be enough to judge
it. Aidan Roantree is the right person to say whether the maths meets your standard, and I
would welcome his verdict too.

I know term starts next week. That is why I am writing now.

Kind regards,

Morgan McKnight
[phone] · [email] · numscoil.ie

---

*≈330 words. Do not attach anything.*

If it needs shortening, cut the flashcards and timed papers from paragraph 2 (the marking and
the phone are what differentiate; breadth of content is not) and the "trialled with real
students" clause from paragraph 5. Do **not** cut paragraph 2's opening sentence, the QR
paragraph, or the sentence about declining to mark unreadable work.

### The mark-from-a-photo claim is scope-limited — do not widen it

**A photograph returns a mark only on exam questions.** `exam_papers/services/work_analysis.py`
decides the mark in code rather than trusting the model, and returns `estimated_mark = None`
when there is no `max_marks` — which is every one of the 516 practice questions. The probe
puts it plainly: *"Practice questions are never marked — no official scheme."* It also refuses
a mark when the page is unreadable, shows no working, or confidence is low.

So "the platform returns a reasoned analysis of their work with a mark based on the official
marking schemes" is an overclaim if it follows two paragraphs about practice questions — the
reader will assume marks apply there. Worse, it breaks in the demo: photograph working on a
practice question and no mark appears.

The email therefore says **"an estimated mark against the official scheme on exam questions"**
and adds that it declines to mark what it cannot read. Both are accurate, and the second is
the stronger sentence for this reader: an examiner trusts a marker that abstains more than one
that always produces a number. Do not soften "estimated" either — the field is literally
`estimated_mark`, and precision about it buys credibility with someone who has marked for the
SEC.

---

## Why each part is there

The order is: who is writing → **what NumScoil is** → what makes it different → the
proposal → the ask. The second step is the one that is easy to skip and cannot be. Opening on
the marking-scheme feature reads as jumping into the middle of a conversation: it is a
differentiator, and a differentiator only means something once the reader knows the category
it differs within.

- **Paragraph 1 orients in one line** — a maths teacher, writing with a proposal. She knows
  within four seconds who this is and what it wants.
- **Paragraph 2 says what the thing actually is**, plainly: an online tutor for LC Maths,
  and the scope of it — practice questions across the course, solutions, flashcards, timed
  papers, and the teacher side. Breadth first, so she is picturing a platform rather than a
  feature.
- **Paragraph 3 is the pivot: "What separates it from a revision website is that it marks."**
  This is where the hook belongs — after context, not before it. Studyclix is the reference
  point she already has in her head, so name the category and step away from it. "Partial
  credit" is the word an examiner notices.
- **Her SEC examining comes at the end of that paragraph, not the start.** Same flattery,
  same relevance, but now it lands on a claim she can actually evaluate rather than being the
  first thing she reads.
- **Paragraph 4 gets the phone and the QR code its own paragraph** because it is the most
  differentiated thing in the product and nothing else in the Irish market does it. "Maths is
  not typed, though" is the line that earns it — it concedes the obvious limitation of typed
  answers before she raises it, which is more persuasive than claiming completeness. The QR
  code is not a feature anyone buys, but it is the detail that makes a teacher believe you
  have watched students use this: it removes the friction that would otherwise kill the whole
  idea.

### On "AI-powered" — deliberately not used as a label

The phrase is the most devalued in edtech and reads as a vendor mailshot, which is the exact
impression this email is built to avoid. There is also direct evidence against it: the earlier
campaign to 120 schools used subject lines such as *"AI-Powered Maths Tutor for Leaving Cert
Students"* and produced two replies. Thin evidence, but it is the only evidence available and
it points the same way.

For a principal who examined for the SEC, "AI marks your students' maths" invites the
accuracy objection rather than interest — *will it mark them wrong?* — plus a data-protection
question.

**So the mechanism is named precisely, once, and framed by what is deterministic:**

> It compares the mathematics directly, so equivalent forms are accepted; AI is used for the
> parts that need judgement, such as written reasoning.

This is accurate — `services/marking.py` attempts algebraic equivalence and numeric
normalisation first and only falls back to GPT — and it is a **better** claim than
"AI-powered". Most marking is actual mathematics rather than a language model guessing, which
is precisely what a maths teacher needs to hear. It answers "how can it read handwriting?"
while pre-empting "can I trust it?".

If she raises AI directly, lean into it: the group's owner runs AI programmes across its
schools, so the appetite exists at Dukes level. Have the sub-processor answer ready (see
`ioe-deal-structures.md`).
- **The vendor sentence sits in paragraph 4, deliberately.** [Company] builds and maintains;
  Morgan authors the content. It answers "who is behind this and who supports it" at the
  point she starts wondering, rather than competing with the product description for
  attention. Present tense throughout — nothing claims the company was there from the start.
  A cold email opening with a company she has never heard of reads as a vendor mailshot; one
  opening with a maths teacher reads as a person.
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

## LinkedIn version

Fits LinkedIn's 300-character limit on a connection-request note (262 characters). If sending
as a normal message instead, there is no such limit — use the email body.

> Ms O'Toole — I teach LC Higher Level maths. NumScoil is an online tutor for LC Maths:
> practice questions, worked solutions, and it marks a student's answer against the official
> marking scheme. Could I show it to you and Aidan Roantree for 20 minutes? — Morgan McKnight

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
