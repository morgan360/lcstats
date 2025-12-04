# Setting Up Email on PythonAnywhere

## Step 1: Create Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Sign in with morganmcknight@gmail.com
3. Click "Create" or "Generate app password"
4. Select "Mail" as the app
5. Copy the 16-character password (something like: `abcd efgh ijkl mnop`)

## Step 2: Add Email Settings to PythonAnywhere .env

SSH into PythonAnywhere:
```bash
ssh morganmck@ssh.eu.pythonanywhere.com
```

Edit your .env file:
```bash
cd ~/lcstats
nano .env
```

Add these lines (replace YOUR_APP_PASSWORD with the password from Step 1):
```bash
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=morganmcknight@gmail.com
EMAIL_HOST_PASSWORD=YOUR_APP_PASSWORD_HERE
DEFAULT_FROM_EMAIL=noreply@lcaimaths.com
TEACHER_EMAIL=morganmcknight@gmail.com
```

Save and exit (Ctrl+X, then Y, then Enter)

## Step 3: Deploy the Code

Pull the latest code:
```bash
cd ~/lcstats
git pull origin main
```

## Step 4: Reload Web App

1. Go to https://eu.pythonanywhere.com/user/morganmck/webapps/
2. Click the green "Reload" button for your web app

## Step 5: Test It!

1. Go to your live site: https://morganmck.pythonanywhere.com
2. Log in as a student
3. Go to any question
4. Click "📧 Contact Teacher"
5. Send a test message
6. Check morganmcknight@gmail.com - you should receive the email!

## Troubleshooting

If emails aren't being sent:

1. Check PythonAnywhere error logs:
   - Web tab → Error log
   - Look for email-related errors

2. Verify Gmail App Password:
   - Make sure you copied it correctly (no spaces)
   - It should be 16 characters

3. Check if 2-Step Verification is enabled:
   - App Passwords only work with 2-Step Verification enabled
   - Enable it at https://myaccount.google.com/security

4. Test email sending from PythonAnywhere console:
   ```bash
   cd ~/lcstats
   source venv/bin/activate
   python manage.py shell
   ```

   Then in the shell:
   ```python
   from django.core.mail import send_mail
   send_mail(
       'Test Subject',
       'Test message',
       'noreply@lcaimaths.com',
       ['morganmcknight@gmail.com'],
       fail_silently=False,
   )
   ```

   If this fails, it will show you the exact error.