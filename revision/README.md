# Revision App - GeoGebra Integration

The **Revision App** provides comprehensive revision modules for Leaving Certificate Maths topics with support for:
- 📝 Markdown text content with LaTeX math
- 🖼️ Images with captions
- 📐 Interactive GeoGebra visualizations
- 🎥 Video tutorials (YouTube, Vimeo, direct URLs)

## Features

### For Teachers (Admin)
- Create revision modules linked to existing topics
- Add multiple sections with mixed content types
- Rich preview of GeoGebra materials
- Inline section editing
- Publish/unpublish modules
- Order management

### For Students
- Browse published revision modules
- View comprehensive revision content
- Interact with GeoGebra visualizations
- Watch embedded video tutorials
- Link directly to practice questions

## Installation & Setup

### 1. Database Migration

Run the following command on your production server:

```bash
python manage.py migrate revision
```

This will create two tables:
- `revision_revisionmodule` - Main revision modules
- `revision_revisionsection` - Individual sections within modules

### 2. Create Media Directory

Ensure the media directory exists for image uploads:

```bash
mkdir -p media/revision/images/
chmod 755 media/revision/images/
```

### 3. Admin Access

Navigate to `/admin/revision/` to start creating revision modules.

## Usage Guide

### Creating a Revision Module

1. **Go to Django Admin** → Revision → Revision Modules → Add
2. **Select a Topic** (from Interactive Lessons)
3. **Enter Module Details:**
   - Title: e.g., "Probability Distributions - Complete Guide"
   - Description: Brief overview of content
   - Order: Display sequence number
4. **Add Sections** using the inline editor
5. **Publish** when ready (check "Is published")

### Adding Sections

Each section supports multiple content types:

#### Text Content
- Supports Markdown formatting
- LaTeX math: `$inline math$` or `$$display math$$`
- Automatically rendered with KaTeX

#### Images
- Upload image files (PNG, JPG, GIF)
- Add optional captions
- Stored in `media/revision/images/`

#### GeoGebra Integration
1. **Create or find a GeoGebra material:**
   - Visit https://www.geogebra.org
   - Create your visualization or find existing materials
   - Note the Material ID from the URL: `geogebra.org/m/abcd1234` → use `abcd1234`

2. **Configure in Admin:**
   - Enable "GeoGebra enabled"
   - Enter Material ID (e.g., `abcd1234`)
   - Set width/height (default: 800x600)
   - Choose toolbar/menu visibility

3. **Preview:**
   - Click on the GeoGebra preview link in admin
   - Test the applet before publishing

#### Video Integration
- **YouTube:** Paste full URL (`https://www.youtube.com/watch?v=...`)
- **Vimeo:** Paste full URL (`https://vimeo.com/...`)
- **Direct:** Use direct video file URLs
- Add optional captions

### Example Section Structure

```
Module: "Probability Distributions"

Section 1: Introduction
- Text: Overview of probability concepts
- Image: Bell curve diagram

Section 2: Normal Distribution
- Text: Explanation of properties
- GeoGebra: Interactive normal curve (material_id: xyz123)
- Text: How to interpret the visualization

Section 3: Worked Example
- Text: Step-by-step solution
- Video: YouTube tutorial on solving problems

Section 4: Practice
- Text: Link to practice questions
```

## URLs

- **Module List:** `/revision/`
- **Module Detail:** `/revision/<topic-slug>/`

Example: `/revision/probability-distributions/`

## GeoGebra Resources

### Finding Material IDs
1. Browse https://www.geogebra.org/materials
2. Open any material
3. URL format: `https://www.geogebra.org/m/MATERIAL_ID`
4. Copy the MATERIAL_ID part only

### Popular LC Maths Topics
- Normal Distribution: Interactive bell curves
- Trigonometry: Unit circle animations
- Functions: Graph transformations
- Geometry: Circle theorems
- Calculus: Derivative visualizations

### Creating Custom Materials
1. Go to https://www.geogebra.org/geometry (or algebra/3d)
2. Create your visualization
3. Save → Get shareable link
4. Extract Material ID from URL

## Templates

### Customization

Edit these files to customize appearance:
- `revision/templates/revision/module_list.html` - Browse page
- `revision/templates/revision/module_detail.html` - Module view

### CSS Variables

The templates use inline styles but respect these design principles:
- Primary color: `#667eea` (purple gradient)
- Accent: `#1976d2` (blue)
- Cards: White with subtle shadows
- Math: Rendered via KaTeX (already loaded in base template)

## Database Models

### RevisionModule
```python
{
    'topic': OneToOne → Topic,
    'title': 'Module title',
    'description': 'Overview text',
    'is_published': Boolean,
    'order': Integer,
    'created_at': DateTime,
    'updated_at': DateTime
}
```

### RevisionSection
```python
{
    'module': ForeignKey → RevisionModule,
    'title': 'Section heading',
    'order': Integer,
    'text_content': 'Markdown content',
    'image': ImageField (optional),
    'image_caption': String,
    'geogebra_enabled': Boolean,
    'geogebra_material_id': String,
    'geogebra_width': Integer (default: 800),
    'geogebra_height': Integer (default: 600),
    'geogebra_show_toolbar': Boolean,
    'geogebra_show_menu': Boolean,
    'video_enabled': Boolean,
    'video_url': URL,
    'video_caption': String,
    'created_at': DateTime,
    'updated_at': DateTime
}
```

## Admin Features

### Module Admin
- List view with topic, section count, publish status
- Filter by topic, publication status, date
- Search by title, description
- Quick edit: order and publish status
- Inline section editing

### Section Admin
- Content type indicators (📝 Text, 🖼️ Image, 📐 GeoGebra, 🎥 Video)
- Rich preview with image thumbnails and GeoGebra links
- Filter by module, content types
- Collapsible fieldsets for clean interface

## Troubleshooting

### GeoGebra not loading
- Check Material ID is correct (no spaces, special characters)
- Verify material is public on geogebra.org
- Check browser console for JavaScript errors
- Ensure `deployggb.js` loads (check network tab)

### Images not displaying
- Verify `MEDIA_URL` and `MEDIA_ROOT` in settings.py
- Check file permissions: `chmod 755 media/revision/images/`
- Ensure web server serves media files in production

### Videos not embedding
- YouTube: Use watch URL, not embed URL
- Vimeo: Use full video URL
- For direct videos: ensure CORS headers allow embedding
- Check video URL is publicly accessible

### Math not rendering
- LaTeX rendering uses KaTeX (loaded in `_base.html`)
- Use `$...$` for inline math, `$$...$$` for display
- Escape special characters: `\{`, `\}`, etc.

## Future Enhancements

Possible additions:
- [ ] Student progress tracking (which modules viewed)
- [ ] Favorite/bookmark modules
- [ ] Print-friendly view
- [ ] PDF export of revision notes
- [ ] Student annotations/notes
- [ ] Quiz integration from revision sections
- [ ] Custom GeoGebra applet parameters
- [ ] LaTeX editor in admin

## Development

### Adding New Content Types

To add new content types to sections:

1. Add fields to `RevisionSection` model
2. Update migration
3. Add fields to admin inline
4. Update template (`module_detail.html`)
5. Add preview logic in admin

### Testing

To test locally:
```bash
python manage.py runserver
# Visit http://localhost:8000/revision/
```

## Support

For issues or questions:
- Check this README
- Review Django admin help text
- Inspect browser console for errors
- Contact system administrator

---

**Version:** 1.0
**Created:** 2025-11-18
**License:** Part of LCAI Maths platform
