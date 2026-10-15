# Promo video: shot list and AI voiceover script

Two cuts from one set of recordings, made in **Screen Studio**. Voiceover generated on
**WaveSpeed** (same service as the NumSkull intro animation).

- **Cut A, site promo:** 60–90 s, captions burned in, music, voiceover optional.
- **Cut B, IoE backup:** about 3½ min, AI voiceover, little or no music. It follows the order
  of the pitch email so it can stand in for the live demo. It is also the **follow-up sent
  after the meeting**, for Yvonne to forward to colleagues, so it must make sense with nobody
  there to explain it. Send it as an **unlisted YouTube link**, never as an attachment (well
  over Gmail's 25 MB) and never public (it shows SEC exam questions).

The student part of the video is **two exam questions, one clip each**:

- **Q1: 2025 Paper 1 Q2.** Ask the help bot, type answers, get partial then full marks, open
  the solution.
- **Q2: 2022 Paper 1 Q8.** Scan the QR code with the phone, photograph the working from your
  own copy, let it mark it, review the feedback. Includes a short phone clip (10–15 s).

Generate the voiceover **one block per file** (`B03.mp3`, etc.) so a single line can be
re-generated without re-timing the rest. Maths is spelled out for TTS. Keep the written
symbols for the captions.

## Claims the voiceover must not make

These come from `ioe-approach-email.md`. Breaking them makes the video show something the
product doesn't do.

- **A photograph gets a mark only on an exam question.** Q2 is an exam question, so the mark
  can be shown and described.
- The photo marker **declines** when the page is unreadable or confidence is low. Don't say
  "always".
- Contextual help is about **the question on screen**. Don't describe it as a library of
  notes.
- "Official marking scheme" applies to **exam questions**. Both questions here are exam
  questions, so it can be said.
- Content figures: **over 500 practice questions across 21 topics**. Recheck the count
  before recording.

## Take 1: 2025 Paper 1 Q2

| Step | Do | Expect |
|---|---|---|
| 1 | Open the question from Interactive Lessons → Exam Questions | Question image, answer boxes for (a)(i) and (a)(ii) |
| 2 | Ask the help bot: **"How do I differentiate sin(ax)?"** | A reply tied to this question. Let it finish before moving on |
| 3 | (a)(i): type the correct answer **`y = 2x + 4cos(4)`** | Full marks |
| 4 | (a)(ii): type the nearly correct **`y - 4x + 6`** | Partial credit and an explanation of the sign slip |
| 5 | (a)(ii): type the correct **`y - 4x - 6`** | Full marks |
| 6 | Open the solution (marking-scheme image) and scroll through it | Solution unlocks because the answer is correct |

Check before recording: the answers above are as typed in the plan. If (a)(i) is meant to be
the derivative, `2x + 4cos(4x)` may be what you want. If (a)(ii) is an equation of a line,
`y = 4x - 6` may read better on screen than `y - 4x - 6`. Do a dry run of steps 3 to 5
first. If a take goes wrong, press **"Start this question over"** on the question: the boxes
empty, the solution locks again and the attempt count starts from zero. The earlier answers
are kept in Ava's reports, which doesn't matter for a demo account.

## Take 2: 2022 Paper 1 Q8

| Step | Do | Expect |
|---|---|---|
| 1 | Open the question as Ava and show its QR code | Question image, QR code on screen |
| 2 | **Phone clip:** scan the QR code, photograph the page of working, send it | Phone shows the photo going up |
| 3 | Back on the desktop, wait for the result. Speed this up in Screen Studio | "Marking", then a mark against the official scheme, plus method feedback |
| 4 | Scroll slowly through the feedback | Long enough to read each point |

**Photos can be sent as many times as needed.** Each QR code opens a fresh upload, a photo
is not a typed attempt (it doesn't count towards unlocking the solution), and earlier photo
results don't reappear on the question page. So Take 2 can be redone as Ava until it's right.
There's a cap on photos per hour, so space the retries out if one is refused.

The phone clip can be recorded in the same take or separately. Separately is easier.
Photograph the same page in both, so the clips match, and cut the phone clip in between
steps 1 and 3.

### Recording the phone clip

Use the iPhone's own screen recording. It captures the camera view too, so the QR scan and
the photo both show.

1. **Add the button once.** Open Control Centre (swipe down from the top-right corner; on an
   iPhone with a Home button, swipe up from the bottom). Press and hold an empty space, tap
   **Add a Control**, and choose **Screen Recording**.
2. **Before recording:**
   - Turn on **Do Not Disturb**.
   - Charge the phone, since the battery shows in the status bar.
   - Leave the microphone off. The voiceover is the sound.
3. **Record.** Open Control Centre, tap **Screen Recording**, and wait for the 3-second
   countdown.
4. **Do the actions slowly:**
   - Point the Camera app at the QR code on the desktop and tap the link.
   - Photograph the page of working.
   - Send it.
5. **Stop.** Tap the red indicator at the top. The clip saves to Photos. **AirDrop** it to
   the Mac.
6. **Edit.** Trim the opening seconds where Control Centre is open. The clip is portrait and
   the video is 16:9: centre it on a plain background matching the title card, or place it
   beside the desktop.

Optional: open with 2–3 s filmed on a second phone (on a stand, good light) of your hand
holding the phone over the paper, then cut to the screen recording. It shows the work being
done on paper, which the screen recording alone doesn't.

Pick a page that is clean and well lit. If the marker declines it, that's correct behaviour,
but it's not the shot you want. Re-shoot the photo rather than the take.

**Before recording, check prod has "Start this question over"** (commit da23bc75 and its
migration, exam_papers 0033). Without it, every typed attempt counts and a part's solution
unlocks after two, so Take 1 would have to be right first time on Ava's account.

## Recording setup (Screen Studio)

- Log in as **Ava Pierce** ("6th Year Demo") for the student shots and as the demo teacher
  for B09. Real students must never appear.
- Record **window only**, the browser at 1920×1080 and 110–125% zoom. Hide the bookmarks bar,
  turn on Do Not Disturb, and use a clean profile.
- Leave **auto-zoom on clicks** on. Before export, check each zoom lands on the answer box,
  the bot reply, or the mark. Remove any that zoom on nothing (e.g. a scroll click).
- Turn on **cursor smoothing** and set a slightly larger cursor. Move the mouse slowly and
  pause for a second on each thing you want the viewer to read.
- Use **speed-up segments** for the grading and photo-marking waits, rather than cutting
  them. The viewer should see that it takes a moment.
- Take 2 has a phone clip, best recorded separately (see Take 2), and cut in before the
  desktop result.
- Export Take 1 and Take 2 as separate clips at 1080p/60. Editing is easier.
- **Cut A is public, and both questions are SEC exam questions.** Either get SEC permission
  first, or in Cut A crop out or blur the question image and show only the answers, bot
  reply and feedback.

---

## Cut B: IoE backup (≈3:30)

| # | On screen | Voiceover block | ≈s |
|---|---|---|---|
| B01 | Title card (see below) | B01 | 3–5 |
| B02 | Dashboard → topic list, scrolling | B02 | 15 |
| B03 | Take 1, steps 1–2: opening 2025 P1 Q2, asking "How do I differentiate sin(ax)?" | B03 | 20 |
| B04 | Take 1, steps 3–5: (a)(i) correct; (a)(ii) nearly right → partial; then correct | B04 | 35 |
| B05 | Take 1, step 6: opening and scrolling the solution | B05 | 12 |
| B06 | Take 2: QR code → phone clip (scan, photograph, send) → mark → feedback | B06 | 40 |
| B07 | Timed past paper, then flashcards (quick) | B07 | 15 |
| B08 | Teacher: assigning homework → class progress | B08 | 30 |
| B09 | End card (see below) | B09 | 10 |

### Title and end cards

Plain and still: white or the site's background colour, the site's font, no mascot, no music
sting. The NumSkull intro belongs in Cut A, for students, not in a video for a principal and
whoever she forwards it to.

**Title card (B01, 3–5 s)**, for a viewer who has had it forwarded with no context:

> **NumScoil**
> An online tutor for Leaving Certificate Higher Level Maths

**End card (B09, hold about 10 s)**, so anyone who watches can reach you:

> **NumScoil**
> numscoil.ie
>
> Morgan McKnight
> morganmcknight@gmail.com

### Voiceover

**B01**
> This is NumScoil. An online tutor for Leaving Certificate Higher Level Maths.

**B02**
> Students work through practice questions and past exam questions covering the whole
> course. That's over five hundred practice questions, across twenty-one topics.

**B03**
> Here's a question from the twenty twenty-five paper. Before she starts, she asks for help
> without leaving the question: how do I differentiate sine of a x? The answer is about this
> question, not a generic explanation she has to go and find.

**B04**
> Then she types her answers, and NumScoil marks each part against the official marking
> scheme. The first part is right. On the second, she makes a sign slip. So she gets partial
> credit, and an explanation of exactly where the marks were lost. She fixes it, and gets
> full marks.

**B05**
> Once she's got it right, or made a real attempt, the marking scheme's solution unlocks, so
> she can check her method against it.

**B06**
> Work done on paper counts too. Here's a question from twenty twenty-two. She scans the
> code with her phone, photographs her working and sends it, and NumScoil reads her method
> and estimates the mark against the official scheme, with feedback on each step. If it
> can't read the page clearly, it says so rather than guessing.

**B07**
> There are past papers under timed conditions, and flashcards for the facts that have to be
> known cold.

**B08**
> Teachers set work for a whole class or for individual students, and see exactly who has
> done what, and how well.

**B09**
> NumScoil. Built in Ireland, for the Leaving Cert. Numscoil dot i e.

---

## Cut A: site promo (≈75 s)

The captions carry the message, because autoplay is muted. The voiceover reuses Cut B's
lines, shortened. See the SEC note under Recording setup before using exam questions here.

| # | On screen | Caption | Voiceover | ≈s |
|---|---|---|---|---|
| A01 | NumSkull intro | **LC Higher Level Maths. Marked as you go.** | A01 | 5 |
| A02 | Take 1: asking the bot about sin(ax) | **Stuck? Ask about *this* question.** | A02 | 10 |
| A03 | Take 1: sign slip → partial credit → corrected → full marks | **Type your answer. Get it marked against the scheme.** | A03 | 18 |
| A04 | Take 1: solution opening | **Then check the official solution.** | — | 5 |
| A05 | Take 2: photo upload → mark → feedback | **Photograph your working. Get it marked.** | A05 | 15 |
| A06 | Quick montage: timed paper, flashcards, topic list | **500+ questions · 21 topics · past papers · flashcards** | — | 10 |
| A07 | Teacher dashboard | **Teachers: set work, see progress.** | — | 6 |
| A08 | End card | **numscoil.ie** | A08 | 5 |

**A01**
> Leaving Cert Higher Level Maths. Marked as you go.

**A02**
> Stuck? Ask about the question you're on.

**A03**
> Type your answer, and NumScoil marks it against the marking scheme, with partial credit and
> an explanation of where the marks went.

**A05**
> Did it on paper? Photograph your working, and get it marked.

**A08**
> NumScoil dot i e.

---

## TTS notes

- Service: **WaveSpeed Desktop → Playground**. Use these settings for every block, so a
  re-generated line matches the rest:
  - model: `elevenlabs/eleven-v4-turbo`, function: `turbo`
  - voice ID: `1e9Gn3OQenGu4rjQ3Du1`
  - stability: 0.5, similarity: 0.75
- Write "NumScoil" as **"Num-Scoil"** in the TTS input — this voice says it correctly
  (tested 2026-10-14). Keep the correct spelling, NumScoil, in the captions.
- Write "numscoil.ie" as **"Num-Scoil dot I E"**.
- Write "sin(ax)" as **"sine of a x"** and years as words ("twenty twenty-five").
- Use one voice and the same settings for every block. Irish-accented, calm, mid-paced.
- Leave about 0.3 s of silence at the start and end of each file to make editing easier.
