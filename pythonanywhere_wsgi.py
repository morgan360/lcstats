# +++++++++++ DJANGO +++++++++++
# To use your own django app use code like this:
import os
import sys
from dotenv import load_dotenv

# Add your project directory to the sys.path
path = '/home/yourusername/lcstats'  # CHANGE 'yourusername' to your PythonAnywhere username
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