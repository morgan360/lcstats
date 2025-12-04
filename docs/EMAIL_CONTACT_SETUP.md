# Student Email Contact Feature

## Overview

Students can now contact you directly from any question page via a "Contact Teacher" button. The email will include all relevant context about the question they're asking about.

## Features

- **Contact Button**: Green "📧 Contact Teacher" button in the InfoBot section of every question
- **Context-Aware**: Automatically includes topic, question number, and section in the email
- **Student Info**: Includes student's name and email for easy reply
- **Admin Link**: Direct link to the question in Django admin for your reference

## How It Works

### For Students:
1. Click "📧 Contact Teacher" button on any question page
2. Fill out subject and message
3. Click "Send Message"
4. Receive confirmation that message was sent
5. Redirected back to the question

### For You (Teacher):
You'll receive an email at **morganmcknight@gmail.com** with:
- Student name and email
- Question details (Topic, Q number, Section)
- Subject and message from student
- Direct admin link to view the question

## Current Configuration

### Local Development
- Uses `console.EmailBackend` (emails print to terminal)
- Perfect for testing without actual email sending

### Production Setup

To enable actual email sending on PythonAnywhere, add these to your `.env` file:

```bash
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@lcaimaths.com
TEACHER_EMAIL=morganmcknight@gmail.com
```

### Gmail App Password Setup

1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification if not already enabled
3. Go to https://myaccount.google.com/apppasswords
4. Generate an "App Password" for "Mail"
5. Use that 16-character password as `EMAIL_HOST_PASSWORD`

**Important**: Never use your actual Gmail password - always use an App Password!

## Testing Locally

To test the feature locally:

```bash
# Start the development server
python manage.py runserver

# Navigate to any question page
# Click "Contact Teacher" button
# Fill out and submit the form

# Check your terminal - you'll see the email content printed there
```

## Files Created/Modified

**New Files:**
- `interactive_lessons/forms.py` - Contact form definition
- `interactive_lessons/templates/interactive_lessons/question_contact.html` - Contact form page

**Modified Files:**
- `interactive_lessons/views.py` - Added `question_contact` view
- `interactive_lessons/urls.py` - Added contact URL route
- `interactive_lessons/templates/interactive_lessons/quiz.html` - Added contact button
- `lcstats/settings.py` - Added email configuration

## Deploying to Production

To deploy this feature to PythonAnywhere:

```bash
# Use the existing migration deploy script
./deploy_migration.exp

# OR manually:
ssh morganmck@ssh.eu.pythonanywhere.com
cd ~/lcstats
git pull origin main
source venv/bin/activate
python manage.py collectstatic --noinput
# Then reload web app from dashboard
```

**After deploying**, add the email environment variables to your `.env` file on PythonAnywhere if you want actual emails (otherwise it will use console backend and log to error log).

## Future Enhancements

Possible improvements:
- Add attachment support for students to send screenshots
- Track email history in database
- Auto-reply confirmation to students
- Rate limiting to prevent spam
- Email threading for conversations

## Troubleshooting

**Emails not sending in production:**
- Check `.env` file has correct EMAIL_BACKEND and credentials
- Verify Gmail App Password is correct
- Check PythonAnywhere error logs for email-related errors
- Ensure TEACHER_EMAIL is set correctly

**Button not showing:**
- Clear browser cache
- Verify you pulled latest code
- Check that quiz.html was updated correctly

**Form errors:**
- Check that user is logged in (feature requires authentication)
- Verify question ID exists in URL
- Check Django logs for detailed error messages