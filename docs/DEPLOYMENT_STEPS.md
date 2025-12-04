# Manual Deployment Steps for PythonAnywhere

Follow these steps in order. I've made it as simple as possible!

## Part 1: Upload Database Backup

Open a terminal and run:

```bash
cd /Users/morgan/lcstats
scp lcaim_backup.sql morganmck@ssh.pythonanywhere.com:~/
```

Enter your PythonAnywhere password when prompted.

---

## Part 2: Connect to PythonAnywhere and Setup

Connect via SSH:

```bash
ssh morganmck@ssh.pythonanywhere.com
```

Once connected, run these commands one by one:

### Clone the repository:
```bash
cd ~
git clone https://github.com/morgan360/lcstats.git
cd lcstats
```

### Create virtual environment:
```bash
python3.10 -m venv venv
source venv/bin/activate
```

### Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install mysqlclient
```

This will take a few minutes. Wait for it to complete.

---

## Part 3: Create MySQL Database

**BEFORE CONTINUING**, open a new browser tab and:

1. Go to https://www.pythonanywhere.com
2. Log in to your account
3. Go to the **Databases** tab
4. Note your MySQL password (or reset it if you don't know it)
5. Create a new database named: `morganmck$lcaim` (or use an existing one)
6. Note these credentials:
   - Database name: `morganmck$lcaim` (or whatever you named it)
   - Username: `morganmck`
   - Password: (your MySQL password)
   - Host: `morganmck.mysql.pythonanywhere-services.com`

---

## Part 4: Create .env File

Back in your SSH session, create the .env file:

```bash
cd ~/lcstats
nano .env
```

Copy and paste this content (UPDATE THE VALUES with your actual credentials):

```env
# Django Settings
SECRET_KEY=6zmp==sw7p^ta%i&o_0sdktl8hh1l+7#8$!f-h4gb%2ux+d2()
DEBUG=False
ALLOWED_HOSTS=morganmck.pythonanywhere.com

# Database (PythonAnywhere MySQL)
DB_NAME=morganmck$lcaim
DB_USER=morganmck
DB_PASSWORD=YOUR_MYSQL_PASSWORD_HERE
DB_HOST=morganmck.mysql.pythonanywhere-services.com
DB_PORT=3306

# OpenAI Configuration
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
OPENAI_PROJECT=YOUR_OPENAI_PROJECT_ID_HERE
OPENAI_ORG_ID=YOUR_OPENAI_ORG_ID_HERE
OPENAI_EMBED_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini
FAQ_MATCH_THRESHOLD=0.7
```

**IMPORTANT: Replace these placeholders:**
- `YOUR_MYSQL_PASSWORD_HERE` - Your PythonAnywhere MySQL password
- `YOUR_OPENAI_API_KEY_HERE` - Your OpenAI API key
- `YOUR_OPENAI_PROJECT_ID_HERE` - Your OpenAI Project ID
- `YOUR_OPENAI_ORG_ID_HERE` - Your OpenAI Organization ID

Save and exit nano:
- Press `Ctrl+X`
- Press `Y` to confirm
- Press `Enter` to save

---

## Part 5: Run Database Migrations

Still in SSH session:

```bash
cd ~/lcstats
source venv/bin/activate
python manage.py migrate
```

---

## Part 6: Import Your Data

Import the database backup:

```bash
mysql -u morganmck -p -h morganmck.mysql.pythonanywhere-services.com morganmck\$lcaim < ~/lcaim_backup.sql
```

Enter your MySQL password when prompted.

---

## Part 7: Collect Static Files

```bash
cd ~/lcstats
source venv/bin/activate
python manage.py collectstatic --noinput
```

---

## Part 8: Create Superuser (Optional)

If you want to create a new superuser:

```bash
python manage.py createsuperuser
```

Or you can use your existing users from the database import.

---

## Part 9: Configure Web App

1. Go to https://www.pythonanywhere.com
2. Click the **Web** tab
3. Click **"Add a new web app"** (if you haven't already created one for this project)
4. Choose **"Manual configuration"** (NOT Django wizard)
5. Select **Python 3.10**

### Configure these settings:

#### Code section:
- **Source code:** `/home/morganmck/lcstats`
- **Working directory:** `/home/morganmck/lcstats`

#### Virtualenv section:
- Enter path: `/home/morganmck/lcstats/venv`

#### WSGI configuration file:
Click on the WSGI configuration file link, then **replace ALL the content** with this:

```python
import os
import sys
from dotenv import load_dotenv

# Add your project directory to the sys.path
path = '/home/morganmck/lcstats'
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

Save the file.

#### Static files section:
Click "Enter URL" and add these two mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/morganmck/lcstats/staticfiles` |
| `/media/` | `/home/morganmck/lcstats/media` |

---

## Part 10: Reload and Test

1. At the top of the Web tab, click the big green **"Reload morganmck.pythonanywhere.com"** button
2. Wait a few seconds
3. Visit: **https://morganmck.pythonanywhere.com**

### Test these features:
- [ ] Home page loads
- [ ] Can access admin at `/admin/`
- [ ] Student login works
- [ ] Questions display with LaTeX rendering
- [ ] Static files (CSS/images) are loading
- [ ] InfoBot/OpenAI features work

---

## Troubleshooting

### View Error Logs

If something doesn't work, check the error logs:

On the Web tab, click on:
- **Error log** - Shows Python errors
- **Server log** - Shows HTTP requests

Or via SSH:
```bash
tail -f /var/log/morganmck.pythonanywhere.com.error.log
```

### Common Issues:

**"DisallowedHost" error:**
- Check ALLOWED_HOSTS in .env file includes `morganmck.pythonanywhere.com`

**Database connection errors:**
- Verify database credentials in .env
- Make sure you escaped the `$` in the database name in the mysql command

**Static files not loading:**
- Run `python manage.py collectstatic --noinput` again
- Check static file mappings in Web tab

**OpenAI errors:**
- Verify API keys in .env file
- Check OpenAI account has sufficient credits

---

## Future Updates

When you make changes to your code:

```bash
ssh morganmck@ssh.pythonanywhere.com
cd ~/lcstats
source venv/bin/activate
git pull origin main
pip install -r requirements.txt  # if dependencies changed
python manage.py migrate  # if models changed
python manage.py collectstatic --noinput  # if static files changed
# Then reload web app from dashboard
```

---

## Summary

You now have:
- ✅ Code deployed from GitHub
- ✅ Virtual environment with all dependencies
- ✅ MySQL database with your data
- ✅ Environment variables configured
- ✅ Static files collected
- ✅ Web app configured

Your site should be live at: **https://morganmck.pythonanywhere.com**

Good luck! 🚀