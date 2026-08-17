# SEC licensing request

**Send this the same week as the IoE email.** The holding line — "a licensing request is
with the SEC and being processed" — is only true once this has actually gone.

## Why

SEC terms of access permit download "solely for their own personal, non-commercial use" and
bar copying, modifying or distributing the material without "express written authorisation of
the State Examinations Commission."

NumScoil currently holds **280 exam questions and 1,090 question parts as images cropped
from SEC papers**, plus marking-scheme PDFs and solution images taken from marking schemes.
Free personal use is arguably within the spirit of that. A €9.99/month subscription is not.

The person being pitched is a former SEC examiner and oral examiner. Whatever the answer, it
is better to hold it than to be asked cold.

## Send to

State Examinations Commission
Cornamaddy, Athlone, Co. Westmeath, N37 TP65

Phone **090-64 83600** first and ask who handles copyright and licensing of examination
material — there is no published legal or corporate-services contact, and a named recipient
will move faster than a general enquiry. Send by email if they give an address, and post a
signed copy as well: a paper letter to a State body creates a record and tends to get
answered.

---

## The letter

---

Morgan McKnight
[address]
[email] · [phone]

[Date]

State Examinations Commission
Cornamaddy
Athlone
Co. Westmeath
N37 TP65

**Re: Request for licence to reproduce examination material on an educational platform**

Dear Sir or Madam,

I am a teacher of Leaving Certificate Higher Level Mathematics. I am writing to ask what
licence or written authorisation the Commission can offer for the reproduction of examination
papers and marking schemes on an online educational platform.

**The platform.** NumScoil (numscoil.ie) is an online tutor for Leaving Certificate
Mathematics. Its core function is automatic marking: a student types an answer, and the
platform marks it against the criteria of the official marking scheme, awards partial credit
and explains the mark. It also holds 516 practice questions covering the Higher Level course,
together with hints and worked solutions. [**See the provenance note below before describing
these as original.**]

**The use I wish to license.** Two things specifically:

1. **Examination questions** from past Leaving Certificate papers, reproduced as cropped
   images of the printed question, shown to a registered student who is attempting that
   question on the platform.
2. **Marking schemes**, reproduced in extract as the worked solution and mark allocation
   shown to that student after they have attempted the question.

The material is presented as the Commission's, unaltered, and is not offered as a download
or a compilation. It is shown to the individual student in the course of attempting the
question.

**Why I am asking.** I intend to place the platform on a paid subscription and to offer it
to schools. That takes the use beyond the "personal, non-commercial use" permitted by the
terms of access on examinations.ie, and I would prefer to hold the Commission's written
position before doing so rather than after.

**Specific questions.** It would help greatly to know:

1. Does the Commission operate a licensing scheme for commercial or subscription-based
   educational use of examination papers and marking schemes, and on what terms?
2. Does the position differ between **question papers** and **marking schemes**?
3. Does it differ where the material is shown to a student who already has free access to
   the same papers on examinations.ie — that is, where the platform provides marking and
   feedback rather than access to the material itself?
4. Are there conditions — attribution, a limit on how much of a paper may appear, a
   prohibition on modification — under which such use would be acceptable?
5. Is there a fee, and is it calculated per paper, per student, or as a share of revenue?

I am content to work within whatever constraints the Commission sets, including removing the
material entirely and confining the platform to my own questions if that is the Commission's
preference. I would rather build the product around the correct answer than discover it
later.

I would be grateful for any guidance, and I am happy to provide access to the platform, or
to travel to Athlone, if it would help you assess the request.

Yours faithfully,

Morgan McKnight

---

## Provenance note — resolve before sending

**Do not describe the 516 practice questions as "my own original work" in a letter to the
rights holder until you can stand over it.** The database cannot establish it:
`is_copyrighted` is True on 202 questions and False on 314, and the field's meaning is
contradictory in the codebase — `Question.is_copyrighted`'s help text reads *"True if this
question is copyrighted (e.g., from published exam papers)"*, while `extract-question.md`
instructs that True means *"Original NumScoil content, copyright owned by NumScoil"*.

You wrote these, so you know which are yours. Before sending:

- Decide the true figure and state that instead — "over 200 questions of my own authorship"
  is stronger than an unsupportable 516, because it survives scrutiny.
- Or drop the provenance claim from the letter entirely. It is not load-bearing: the letter
  asks about *SEC* material, and the originality of the rest is a side point.

This matters more here than anywhere else. Overstating your own authorship in a written
request to the body whose copyright you are asking about is the one error that would turn a
routine licensing question into a reason to refuse.

**Separately, fix the flag.** Two parts of the codebase document it in opposite directions,
so neither the data nor any future claim built on it can be trusted until the convention is
settled and the existing rows are corrected.

## Notes on the letter

**What it deliberately does not do:**

- It does not describe the existing use as already commercial and at scale. The current state
  is a free platform with 19 non-staff users; the letter asks about the intended use. That is
  accurate and it is not an admission.
- It does not ask for forgiveness, which would invite a cease-and-desist rather than a
  licence.
- It does not argue fair dealing or educational exemption. Asserting a legal position to the
  rights holder invites a legal reply; asking a commercial question invites a commercial one.

**Question 3 is the one that matters most.** If the Commission accepts that marking a
student's attempt is different from redistributing the paper — the student having free access
to it either way — then the product works as designed. That framing is genuinely
distinguishable and is the strongest ground available.

**The closing offer to remove the material is deliberate.** It costs nothing, it signals good
faith to a State body, and it is true: the fallback below is viable.

## Fallback if the answer is no

The product becomes the practice questions plus the marking engine:

- SEC questions are **linked**, not reproduced — the student opens the paper on
  examinations.ie themselves.
- NumScoil marks their typed answer and shows a worked solution that is **original**, written
  fresh rather than lifted from the scheme.
- The 280 exam questions come off the platform, or become staff-only.

Smaller, entirely clean, and sellable. Worth knowing which version is being sold before the
IoE meeting rather than during it.

## Follow up

State bodies are slow. If nothing after **three weeks**, phone the number above and ask for
the status by reference to the date sent. Log the reply — or the absence of one — here, since
what was asked and when is what makes the holding line defensible.

| Date | Action | Outcome |
|---|---|---|
| | Phoned to identify the right recipient | |
| | Letter sent (email / post) | |
| | Follow-up call | |
| | Reply received | |
