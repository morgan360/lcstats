# Flashcard Import/Export Guide

This guide explains how to export and import flashcards using Django management commands.

## Overview

The import/export system allows you to:
- **Backup** flashcard sets
- **Share** flashcards between environments (dev/staging/production)
- **Version control** flashcard content
- **Bulk edit** flashcards in JSON format
- **Transfer** flashcards between databases

---

## Export Flashcards

Export flashcards from the database to a JSON file.

### Basic Usage

```bash
# Export all flashcards
python manage.py export_flashcards output.json

# Export with pretty formatting
python manage.py export_flashcards output.json --pretty

# Export with images (base64 encoded)
python manage.py export_flashcards output.json --include-images --pretty
```

### Filtered Export

```bash
# Export only a specific topic
python manage.py export_flashcards circles.json --topic coordinate-geometry

# Export only a specific set (by ID)
python manage.py export_flashcards set_3.json --set 3

# Combine filters
python manage.py export_flashcards output.json --topic probability --include-images
```

### Export Options

| Option | Description |
|--------|-------------|
| `--topic SLUG` | Export only flashcards from this topic (e.g., `--topic differentiation`) |
| `--set ID` | Export only flashcards from this set (e.g., `--set 3`) |
| `--include-images` | Include images as base64 encoded data (increases file size) |
| `--pretty` | Pretty-print JSON for readability |

### Output Format

The exported JSON file has this structure:

```json
{
  "version": "1.0",
  "export_metadata": {
    "include_images": true
  },
  "sets": [
    {
      "topic": {
        "name": "Coordinate Geometry",
        "slug": "coordinate-geometry"
      },
      "set": {
        "title": "Circles",
        "description": "Equations of circles...",
        "order": 1,
        "is_published": true
      },
      "cards": [
        {
          "order": 1,
          "front_text": "What is the equation...",
          "back_text": "$x^2 + y^2 = 25$",
          "distractor_1": "$x^2 + y^2 = 5$",
          "distractor_2": "...",
          "distractor_3": "...",
          "explanation": "For a circle...",
          "front_image": "base64encodeddata...",
          "front_image_name": "circle.png",
          "back_image": "base64encodeddata...",
          "back_image_name": "circle_back.png"
        }
      ]
    }
  ]
}
```

---

## Import Flashcards

Import flashcards from a JSON file into the database.

### Basic Usage

```bash
# Import flashcards from file
python manage.py import_flashcards input.json

# Preview import without making changes
python manage.py import_flashcards input.json --dry-run
```

### Handling Existing Sets

```bash
# Skip sets that already exist
python manage.py import_flashcards input.json --skip-existing

# Overwrite existing sets (deletes and recreates)
python manage.py import_flashcards input.json --overwrite
```

### Import Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview import without making changes |
| `--skip-existing` | Skip flashcard sets that already exist |
| `--overwrite` | Delete and recreate existing sets |

### Import Behavior

**Topics:**
- If topic doesn't exist → **Created**
- If topic exists → **Reused**

**Flashcard Sets:**
- Default: Error if set exists (prevents accidents)
- `--skip-existing`: Skip if exists
- `--overwrite`: Delete old, create new

**Images:**
- Automatically detected from JSON
- Base64 images decoded and saved to `media/flashcards/`

---

## Common Workflows

### 1. Backup All Flashcards

```bash
# Create a backup with images
python manage.py export_flashcards backup_$(date +%Y%m%d).json --include-images --pretty

# Example output: backup_20250128.json
```

### 2. Share Flashcards Between Developers

**On source machine:**
```bash
python manage.py export_flashcards flashcards_to_share.json --include-images
```

**On target machine:**
```bash
python manage.py import_flashcards flashcards_to_share.json --skip-existing
```

### 3. Bulk Edit Flashcards

```bash
# 1. Export to JSON
python manage.py export_flashcards edit_me.json --pretty --topic differentiation

# 2. Edit the JSON file in your editor
# (Fix typos, update explanations, etc.)

# 3. Import back (overwrite)
python manage.py import_flashcards edit_me.json --overwrite
```

### 4. Version Control Your Flashcards

```bash
# Export to version-controlled directory
python manage.py export_flashcards flashcards/circles.json --topic coordinate-geometry --pretty

# Commit to git
git add flashcards/circles.json
git commit -m "Add circle flashcards"

# On another machine, import from git
git pull
python manage.py import_flashcards flashcards/circles.json --skip-existing
```

### 5. Deploy to Production

**On staging:**
```bash
python manage.py export_flashcards production_flashcards.json --include-images
```

**On production:**
```bash
# Preview first
python manage.py import_flashcards production_flashcards.json --dry-run

# If looks good, import
python manage.py import_flashcards production_flashcards.json --skip-existing
```

### 6. Test Import Before Applying

```bash
# Always test with --dry-run first!
python manage.py import_flashcards new_flashcards.json --dry-run

# Review the output, then:
python manage.py import_flashcards new_flashcards.json
```

---

## Tips & Best Practices

### Images

**With images (--include-images):**
- ✅ Portable - everything in one file
- ✅ Easy to share
- ⚠️ Large file size (base64 encoding = ~33% larger)

**Without images:**
- ✅ Small file size
- ✅ Fast export/import
- ⚠️ Images not included - need to transfer separately
- 💡 Use for version control (commit JSON, gitignore media files)

### File Organization

Good structure for version-controlled flashcards:

```
flashcards/
├── coordinate_geometry/
│   ├── circles.json
│   ├── lines.json
│   └── parabolas.json
├── differentiation/
│   ├── basic_rules.json
│   └── chain_rule.json
└── README.md
```

### Safety

**Always use --dry-run first:**
```bash
python manage.py import_flashcards risky_file.json --dry-run
```

**Backup before overwriting:**
```bash
python manage.py export_flashcards backup_before_overwrite.json --include-images
python manage.py import_flashcards new_version.json --overwrite
```

### Editing JSON

When editing exported JSON:
1. Use `--pretty` for readable output
2. Validate JSON syntax before importing
3. Keep the structure intact (don't remove keys)
4. Test with `--dry-run` after editing

---

## Troubleshooting

### "Set already exists" Error

```bash
# Solution 1: Skip existing sets
python manage.py import_flashcards input.json --skip-existing

# Solution 2: Overwrite (careful!)
python manage.py import_flashcards input.json --overwrite
```

### "Invalid JSON file" Error

Check your JSON syntax:
```bash
# Validate JSON
python -m json.tool input.json > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Or use jq
jq . input.json
```

### Images Not Importing

Check if images were included in export:
```json
{
  "export_metadata": {
    "include_images": true  // Should be true
  }
}
```

If false, images weren't exported. Re-export with `--include-images`.

### Large File Size

If export file is too large:
- Export without images: Remove `--include-images`
- Transfer images separately
- Compress: `gzip output.json` → `output.json.gz`

---

## Examples

### Complete Backup & Restore

```bash
# Full backup
python manage.py export_flashcards full_backup_$(date +%Y%m%d).json --include-images

# Later, restore on new database
python manage.py import_flashcards full_backup_20250128.json
```

### Selective Export/Import

```bash
# Export just one topic
python manage.py export_flashcards trig.json --topic trigonometry --pretty

# Import to different environment
python manage.py import_flashcards trig.json --skip-existing
```

### CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
- name: Export flashcards
  run: python manage.py export_flashcards flashcards.json --include-images

- name: Upload artifact
  uses: actions/upload-artifact@v2
  with:
    name: flashcards
    path: flashcards.json
```

---

## File Format Reference

### Minimal Valid Import File

```json
{
  "version": "1.0",
  "sets": [
    {
      "topic": {
        "name": "Algebra",
        "slug": "algebra"
      },
      "set": {
        "title": "Quadratics",
        "description": "",
        "order": 0,
        "is_published": true
      },
      "cards": [
        {
          "order": 1,
          "front_text": "Question?",
          "back_text": "Answer",
          "distractor_1": "Wrong 1",
          "distractor_2": "Wrong 2",
          "distractor_3": "Wrong 3",
          "explanation": ""
        }
      ]
    }
  ]
}
```

### Required Fields

**Topic:**
- `name` (string)
- `slug` (string)

**Set:**
- `title` (string)
- `description` (string, can be empty)
- `order` (integer)
- `is_published` (boolean)

**Card:**
- `front_text` (string)
- `back_text` (string)
- `distractor_1` (string)
- `distractor_2` (string)
- `distractor_3` (string)
- `order` (integer)
- `explanation` (string, can be empty)

**Optional Fields:**
- `front_image` (base64 string)
- `front_image_name` (string)
- `back_image` (base64 string)
- `back_image_name` (string)

---

## Support

If you encounter issues:
1. Check JSON syntax
2. Use `--dry-run` to preview
3. Check Django logs for errors
4. Verify file permissions for media directory
