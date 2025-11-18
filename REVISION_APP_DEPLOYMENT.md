# Revision App with GeoGebra Integration - Deployment Guide

## Overview

The Revision App has been successfully integrated into LCAI Maths, providing comprehensive revision modules with GeoGebra interactive visualizations, text content, images, and videos.

## What Was Added

### New Django App: `revision`

```
revision/
├── __init__.py
├── admin.py              # Rich admin interface with preview
├── apps.py
├── models.py             # RevisionModule & RevisionSection
├── views.py              # module_list, module_detail
├── urls.py
├── README.md             # Comprehensive documentation
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py   # Database schema
└── templates/
    └── revision/
        ├── module_list.html    # Browse all modules
        └── module_detail.html  # View module with GeoGebra
```

### Modified Files

1. **`lcstats/settings.py`**
   - Added `'revision'` to `INSTALLED_APPS`

2. **`lcstats/urls.py`**
   - Added `path('revision/', include('revision.urls'))`

3. **`lcstats/__init__.py`**
   - Added PyMySQL configuration for MySQL compatibility

4. **`templates/_base.html`**
   - Added "Revision" link to main navigation

## Deployment Steps

### 1. Pull the Latest Code

```bash
cd /path/to/lcstats
git pull origin claude/integrate-geogebra-01MDSVuJ8mSFbNWLqc2XVjRJ
```

### 2. Run Database Migrations

```bash
python manage.py migrate revision
```

This creates two tables:
- `revision_revisionmodule`
- `revision_revisionsection`

### 3. Create Media Directory

```bash
mkdir -p media/revision/images/
chmod 755 media/revision/images/
chown www-data:www-data media/revision/images/  # Adjust user as needed
```

### 4. Collect Static Files (if needed)

```bash
python manage.py collectstatic --noinput
```

### 5. Restart Application Server

```bash
# For PythonAnywhere
touch /var/www/your_username_pythonanywhere_com_wsgi.py

# For systemd
sudo systemctl restart your-app-name

# For Apache
sudo service apache2 restart
```

## Verification

### 1. Check Admin Interface

- Visit `/admin/revision/`
- You should see:
  - Revision Modules
  - Revision Sections

### 2. Create Test Module

1. Go to Admin → Revision → Revision Modules → Add
2. Select a topic (e.g., "Probability")
3. Enter title: "Test Revision Module"
4. Check "Is published"
5. Add a section with some text
6. Save

### 3. View on Frontend

- Visit `/revision/`
- You should see your test module
- Click to view details
- Verify all content displays correctly

### 4. Test GeoGebra

1. Find a GeoGebra material at https://www.geogebra.org
2. Example: Normal Distribution (material ID: `kw25eqfq`)
3. Add to a section:
   - Enable GeoGebra
   - Enter material ID
   - Save
4. View on frontend - GeoGebra applet should load

## Features Available

### For Teachers (Admin Panel)

1. **Create Revision Modules**
   - Link to existing topics
   - Add multiple sections per module
   - Rich preview of content

2. **Content Types Supported**
   - 📝 Markdown text with LaTeX math
   - 🖼️ Images with captions
   - 📐 GeoGebra interactive visualizations
   - 🎥 Video embeds (YouTube, Vimeo, direct URLs)

3. **Management Features**
   - Publish/unpublish modules
   - Order modules and sections
   - Search and filter
   - Content preview

### For Students (Frontend)

1. **Browse Revision Modules**
   - `/revision/` - All published modules
   - Beautiful card-based layout
   - Filter by topic

2. **View Module Content**
   - `/revision/<topic-slug>/` - Full module with sections
   - Interactive GeoGebra applets
   - Math rendering via KaTeX
   - Video playback
   - Link to practice questions

## URLs Structure

```
/revision/                          → List all modules
/revision/probability-distributions/ → Specific module
/revision/calculus/                 → Another module
```

## GeoGebra Integration

### How It Works

1. **GeoGebra API** loaded via CDN: `deployggb.js`
2. **Material IDs** from https://www.geogebra.org
3. **Embedded** as interactive applets in sections
4. **Configurable**: width, height, toolbar, menu visibility

### Getting Material IDs

1. Browse https://www.geogebra.org/materials
2. Search for topic (e.g., "normal distribution")
3. Open material
4. URL: `https://www.geogebra.org/m/kw25eqfq`
5. Material ID: `kw25eqfq`

### Recommended Materials for LC Maths

- **Statistics:**
  - Normal Distribution: `kw25eqfq`
  - Box Plots: Search on GeoGebra

- **Trigonometry:**
  - Unit Circle: Multiple available
  - Sine/Cosine Waves: Search "trigonometric functions"

- **Calculus:**
  - Derivatives: Search "derivative calculator"
  - Integration: Search "area under curve"

- **Geometry:**
  - Circle Theorems: Multiple available
  - Transformations: Search "geometric transformations"

## Security Notes

1. **Image Uploads**
   - Stored in `media/revision/images/`
   - Ensure proper permissions
   - Consider file size limits

2. **GeoGebra Content**
   - Loaded from geogebra.org CDN
   - Material IDs are public
   - No security risk

3. **Video Embeds**
   - YouTube/Vimeo: Safe iframe embeds
   - Direct URLs: Ensure HTTPS

4. **Admin Access**
   - Only staff users can create modules
   - Students have read-only access

## Troubleshooting

### Issue: GeoGebra not loading

**Symptoms:** Blank space where GeoGebra should be

**Solutions:**
- Check Material ID is correct (no spaces)
- Verify material is public on geogebra.org
- Check browser console for JavaScript errors
- Ensure internet connectivity (loads from CDN)

### Issue: Images not displaying

**Symptoms:** Broken image icons

**Solutions:**
```bash
# Check permissions
ls -la media/revision/images/

# Fix permissions
chmod 755 media/revision/images/
chown www-data:www-data media/revision/images/*

# Verify MEDIA_URL in settings
python manage.py shell
>>> from django.conf import settings
>>> print(settings.MEDIA_URL)
>>> print(settings.MEDIA_ROOT)
```

### Issue: Math not rendering

**Symptoms:** Raw LaTeX visible (e.g., `$x^2$`)

**Solutions:**
- KaTeX loaded in `_base.html` - should work automatically
- Check browser console for KaTeX errors
- Verify delimiters: `$...$` for inline, `$$...$$` for display

### Issue: Videos not embedding

**Symptoms:** No video player visible

**Solutions:**
- YouTube: Use full watch URL, not shortened
- Check video is public/embeddable
- Verify URL format in admin
- Test in different browser

## Database Schema

### revision_revisionmodule

| Column | Type | Description |
|--------|------|-------------|
| id | BigInt | Primary key |
| topic_id | BigInt | FK to interactive_lessons_topic (UNIQUE) |
| title | VARCHAR(200) | Module title |
| description | TEXT | Overview |
| is_published | BOOLEAN | Visibility to students |
| order | INT | Display sequence |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-updated |

### revision_revisionsection

| Column | Type | Description |
|--------|------|-------------|
| id | BigInt | Primary key |
| module_id | BigInt | FK to revision_revisionmodule |
| title | VARCHAR(200) | Section heading |
| order | INT | Display sequence |
| text_content | TEXT | Markdown/LaTeX content |
| image | VARCHAR(100) | File path |
| image_caption | VARCHAR(200) | Image description |
| geogebra_enabled | BOOLEAN | Show GeoGebra |
| geogebra_material_id | VARCHAR(100) | GeoGebra Material ID |
| geogebra_width | INT | Applet width (px) |
| geogebra_height | INT | Applet height (px) |
| geogebra_show_toolbar | BOOLEAN | Show toolbar |
| geogebra_show_menu | BOOLEAN | Show menu |
| video_enabled | BOOLEAN | Show video |
| video_url | VARCHAR(200) | Video URL |
| video_caption | VARCHAR(200) | Video description |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-updated |

## Backup Considerations

### Before Deployment

```bash
# Backup database
mysqldump -u username -p lcaim > lcaim_backup_$(date +%Y%m%d).sql

# Backup media files
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/
```

### After Issues

```bash
# Restore database
mysql -u username -p lcaim < lcaim_backup_YYYYMMDD.sql

# Restore media
tar -xzf media_backup_YYYYMMDD.tar.gz
```

## Performance Optimization

### Database Queries

The app uses optimized queries:
- `select_related()` for topic relationships
- `prefetch_related()` for sections
- `annotate()` for section counts

### Caching (Future)

Consider adding:
```python
# In views.py
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def module_list(request):
    ...
```

### GeoGebra Loading

- Loads asynchronously from CDN
- Doesn't block page rendering
- Consider adding loading indicators

## Next Steps

### Content Creation

1. **Create modules for all LC topics:**
   - Probability & Statistics
   - Calculus
   - Trigonometry
   - Algebra
   - Geometry
   - Complex Numbers
   - Financial Maths

2. **Add GeoGebra visualizations:**
   - Find or create materials on geogebra.org
   - Test each material before adding
   - Document material IDs for backup

3. **Add videos:**
   - Create tutorial videos
   - Or link to quality YouTube content
   - Ensure permissions for embedded content

### Future Enhancements

- [ ] Student progress tracking (which modules viewed)
- [ ] Favorite/bookmark functionality
- [ ] Print-friendly view
- [ ] PDF export
- [ ] Student annotations
- [ ] Quiz integration
- [ ] Mobile app support
- [ ] Offline access

## Support & Documentation

- **Full Documentation:** `/revision/README.md`
- **Django Admin:** `/admin/revision/`
- **Frontend:** `/revision/`

For questions or issues:
1. Check this deployment guide
2. Review app README
3. Test in admin panel
4. Check browser console for errors

---

**Deployed:** 2025-11-18
**Version:** 1.0
**Branch:** claude/integrate-geogebra-01MDSVuJ8mSFbNWLqc2XVjRJ
