# Deployment Notes - Maths vs Physics Data

## Issue Identified

Your local database contains:
- **19 Maths topics** with 495 questions (697 question parts)
- **11 Physics topics** with 1 question (about Diodes - ID 532)

Your production server likely only has the **19 Maths topics**, which creates a discrepancy when using the original sync scripts that export ALL topics.

## Solution

Created a new deployment script: **`sync_maths_only_to_production.sh`**

This script:
- ✅ Exports ONLY Maths topics, sections, questions, and notes
- ❌ Excludes all Physics data (including the 1 Diodes question)
- Prevents foreign key errors on production server
- Keeps Maths and Physics development separate

## What Will Be Exported

When you run `./deployment/sync_maths_only_to_production.sh`:

```
Topics:         19 (Maths only)
Sections:       175
Questions:      495
Question Parts: 697
Notes:          5
```

**Excluded:**
- 11 Physics topics
- 1 Physics question (ID 532 - Diodes)

## Usage

### Option 1: Use the New Maths-Only Script (Recommended)

```bash
./deployment/sync_maths_only_to_production.sh
```

This will:
1. Export only Maths data to 5 JSON files
2. Upload to PythonAnywhere (or provide manual upload instructions)
3. Give you commands to run on PythonAnywhere to import the data

### Option 2: Continue Using Original Script

If your production server already has both Maths and Physics topics set up:

```bash
./deployment/sync_to_production_simple.sh
```

This will export ALL topics (both Maths and Physics).

## Recent Questions Added

The following Complex Numbers questions were just added and will be included in the export:

**Polar Form of Complex Numbers (3 questions):**
- Question 533: Convert $-1 + \sqrt{3}i$ to polar form
- Question 534: Convert $-3 - 3i$ to polar form
- Question 535: Convert $2 - 2\sqrt{3}i$ to polar form

**Division and Multiplication with Polar Form (3 questions):**
- Question 536: Multiply and divide complex numbers in polar form
- Question 537: Operations with different quadrant angles
- Question 538: Find unknown complex number given product

**Applications of De Moivre's Theorem (3 questions):**
- Question 539: $(1 + i)^{10}$ using De Moivre's Theorem
- Question 540: $(\sqrt{3} - i)^6$ using De Moivre's Theorem
- Question 541: Prove $\cos 3\theta = 4\cos^3\theta - 3\cos\theta$

**Finding the Roots of Complex Numbers (3 questions):**
- Question 542: Fourth roots of $8i$ (multi-part with diagrams)
- Question 543: Cube roots of $-1 - \sqrt{3}i$ (multi-part with diagrams)
- Question 544: Fourth roots of $-16$ in rectangular form

**Total new questions:** 12 questions (all in Complex Numbers topic)

## Deployment Script Comparison

| Script | Exports | Use Case |
|--------|---------|----------|
| `sync_to_production_simple.sh` | All Topics (Maths + Physics) | Full sync including Physics |
| `sync_maths_only_to_production.sh` | Maths Topics only | **Recommended for current production** |
| `sync_questions_safe.sh` | All Topics | Advanced sync with backup |

## Recommendation

**Use `sync_maths_only_to_production.sh`** for your current deployment since:
1. Production likely doesn't have Physics topics yet
2. Avoids foreign key constraint errors
3. Exports the 12 new Complex Numbers questions
4. Keeps Physics development separate until ready

## Files That Will Be Created

After running the Maths-only script, you'll get files like:
```
maths_topics_20260201_132400.json      (19 topics)
maths_sections_20260201_132400.json    (175 sections)
maths_questions_20260201_132400.json   (495 questions)
maths_parts_20260201_132400.json       (697 question parts)
maths_notes_20260201_132400.json       (5 notes)
```

The timestamp format is: `YYYYMMDD_HHMMSS`