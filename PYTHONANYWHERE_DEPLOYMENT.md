# PythonAnywhere Deployment Guide for LCAI Maths

## Prerequisites
- PythonAnywhere paid account with SSH access
- Git repository access (GitHub/GitLab)
- OpenAI API key and organization ID

## Step 1: Connect to PythonAnywhere via SSH

```bash
ssh yourusername@ssh.pythonanywhere.com
```

Replace `yourusername` with your PythonAnywhere username.

## Step 2: Clone Your Repository

```bash
cd ~
git clone https://github.com/yourusername/lcstats.git
# Or if using a different repository URL, use that instead
cd lcstats
```

## Step 3: Create Virtual Environment

```bash
mkvirtualenv --python=/usr/bin/python3.10 lcstats-env
# Or use: python3.10 -m venv venv && source venv/bin/activate
```

## Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install mysqlclient  # MySQL driver for PythonAnywhere
```

## Step 5: Create MySQL Database

1. Go to PythonAnywhere Dashboard → Databases tab
2. Create a new MySQL database (if not already created)
3. Note your database credentials:
   - Database name: `yourusername$lcaim` (or create `yourusername$lcai`)
   - Username: `yourusername`
   - Password: (the one you set)
   - Host: `yourusername.mysql.pythonanywhere-services.com`

## Step 6: Create .env File

Create a `.env` file in the project root (`~/lcstats/.env`):

```bash
nano .env
```

Add the following content (update with your actual values):

```env
# Django Settings
SECRET_KEY=your-new-secret-key-here-generate-a-random-one
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com

# Database (PythonAnywhere MySQL)
DB_NAME=yourusername$lcaim
DB_USER=yourusername
DB_PASSWORD=your-mysql-password-from-pythonanywhere
DB_HOST=yourusername.mysql.pythonanywhere-services.com
DB_PORT=3306

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_PROJECT=your-openai-project-id
OPENAI_ORG_ID=your-openai-org-id
OPENAI_EMBED_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini
FAQ_MATCH_THRESHOLD=0.7
```

**To generate a new SECRET_KEY:**
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Save and exit (Ctrl+X, then Y, then Enter in nano).

## Step 7: Run Database Migrations

```bash
cd ~/lcstats
workon lcstats-env  # Activate virtual environment
python manage.py migrate
```

## Step 8: Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

## Step 9: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

## Step 10: Configure Web App on PythonAnywhere Dashboard

1. Go to **Web** tab in PythonAnywhere Dashboard
2. Click **Add a new web app**
3. Choose **Manual configuration** (not Django wizard)
4. Select Python version (3.10 recommended)

### Configure the following sections:

#### Code Section:
- **Source code:** `/home/yourusername/lcstats`
- **Working directory:** `/home/yourusername/lcstats`

#### Virtualenv Section:
- **Virtual environment:** `/home/yourusername/.virtualenvs/lcstats-env`
  (or the path to your venv if you created it differently)

#### WSGI Configuration File:
Click on the WSGI configuration file link and replace the entire content with:

```python
import os
import sys
from dotenv import load_dotenv

# Add your project directory to the sys.path
path = '/home/yourusername/lcstats'
if path not in sys.path:
    sys.path.insert(0, path)

# Load environment variables from .env file
load_dotenv(os.path.join(path, '.env'))

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'lcstats.settings'

# Import Django and setup
import django
django.setup()

# Import the Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Remember to replace `yourusername` with your actual PythonAnywhere username!**

#### Static Files Section:
Add the following mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/yourusername/lcstats/staticfiles` |
| `/media/` | `/home/yourusername/lcstats/media` |

## Step 11: Reload Web App

Click the **Reload** button on the Web tab (big green button at the top).

## Step 12: Test Your Site

Visit: `https://yourusername.pythonanywhere.com`

Test the following:
- Home page loads
- Can log in to admin at `/admin/`
- Static files are loading (CSS, JS, images)
- Student login/registration works
- Questions load correctly with LaTeX rendering
- OpenAI integration works (try InfoBot)

## Troubleshooting

### View Error Logs
On PythonAnywhere Web tab, click on error log and server log links to see detailed errors.

Or via SSH:
```bash
tail -f /var/log/yourusername.pythonanywhere.com.error.log
tail -f /var/log/yourusername.pythonanywhere.com.server.log
```

### Common Issues:

1. **Import errors:** Make sure virtual environment is properly set in Web tab
2. **Static files not loading:** Run `collectstatic` again and check static file mappings
3. **Database connection errors:** Verify database credentials in `.env` file
4. **OpenAI errors:** Check API keys are correct and have sufficient credits

### Database Issues:
If you need to reset the database:
```bash
python manage.py flush  # WARNING: Deletes all data!
python manage.py migrate
python manage.py createsuperuser
```

### Update Deployment:
When you make changes to your code:
```bash
ssh yourusername@ssh.pythonanywhere.com
cd ~/lcstats
workon lcstats-env
git pull origin main  # or your branch name
pip install -r requirements.txt  # if dependencies changed
python manage.py migrate  # if models changed
python manage.py collectstatic --noinput  # if static files changed
# Reload web app from Dashboard
```

## Data Migration from Local Database

If you need to migrate existing data from your local MySQL database:

### Option 1: Using Django dumpdata/loaddata

**On your local machine:**
```bash
python manage.py dumpdata --natural-foreign --natural-primary \
  --exclude contenttypes --exclude auth.Permission \
  --indent 2 > data_dump.json
```

**Copy to PythonAnywhere:**
```bash
scp data_dump.json yourusername@ssh.pythonanywhere.com:~/lcstats/
```

**On PythonAnywhere:**
```bash
cd ~/lcstats
workon lcstats-env
python manage.py loaddata data_dump.json
```

### Option 2: Using MySQL dump

**On your local machine:**
```bash
mysqldump -u morgan -p lcaim > lcaim_backup.sql
```

**Copy to PythonAnywhere:**
```bash
scp lcaim_backup.sql yourusername@ssh.pythonanywhere.com:~/
```

**On PythonAnywhere:**
```bash
mysql -u yourusername -p -h yourusername.mysql.pythonanywhere-services.com yourusername\$lcaim < lcaim_backup.sql
```

## Security Checklist

- [ ] DEBUG set to False in production .env
- [ ] SECRET_KEY is unique and not committed to git
- [ ] Database credentials are in .env, not in settings.py
- [ ] .env file is in .gitignore
- [ ] ALLOWED_HOSTS properly configured
- [ ] OpenAI API keys secured in .env
- [ ] Regular backups of database configured

## Performance Considerations

With a paid PythonAnywhere account, you have:
- More CPU seconds per day
- Ability to use external APIs (OpenAI)
- MySQL database access
- SSH access

**OpenAI Rate Limits:**
- Monitor your OpenAI usage to avoid hitting rate limits
- Consider implementing caching for embeddings (already done with MD5 hash)
- The note embedding system already caches embeddings

**Database Optimization:**
- Ensure database indexes are optimal for your queries
- Use `select_related()` and `prefetch_related()` in views to reduce queries
- Monitor slow queries in production

## Maintenance

**Regular Tasks:**
1. Monitor error logs weekly
2. Check OpenAI API usage and costs
3. Backup database monthly (at minimum)
4. Update dependencies for security patches
5. Monitor disk space usage

**Updating Django/Dependencies:**
```bash
pip install --upgrade Django
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push
```

Then on PythonAnywhere, pull changes and reload.

## Support

- PythonAnywhere Help: https://help.pythonanywhere.com/
- Django Documentation: https://docs.djangoproject.com/
- Your project documentation: See CLAUDE.md

---

**Note:** This is your third site on PythonAnywhere. Make sure you're not exceeding your plan limits for number of web apps.