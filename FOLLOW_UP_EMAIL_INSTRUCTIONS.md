# 📧 How to Send Follow-Up Emails via Production Django Admin

**Date**: January 24, 2026
**Deadline**: January 31, 2026 (7 days away)
**Target**: ~105 schools who received initial email
**Open Rate**: 67.6% (25 schools opened)

---

## ✅ Pre-Flight Checklist

Before you start, make sure:

1. ✅ **Templates are deployed** to production:
   - `schools/templates/schools/emails/follow_up.txt`
   - `schools/templates/schools/emails/follow_up.html`

2. ✅ **Admin code is updated** with follow-up template support
   - File: `schools/admin.py` (lines 180-186)

3. ✅ **SendGrid is configured** in production `.env`:
   - `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
   - `EMAIL_HOST=smtp.sendgrid.net`
   - Your API key is set

---

## 🚀 Step-by-Step Instructions

### Step 1: Deploy Updated Code to Production

If you haven't already deployed the follow-up templates and admin updates:

```bash
# On your local machine
cd /Users/morgan/lcstats

# Add the new files
git add schools/templates/schools/emails/follow_up.txt
git add schools/templates/schools/emails/follow_up.html
git add schools/admin.py

# Commit
git commit -m "Add follow-up email templates and admin support"

# Push to production
git push origin main

# SSH into your production server and pull
ssh your-production-server
cd /path/to/lcstats
git pull origin main

# Restart Django (adjust command based on your deployment)
sudo systemctl restart gunicorn  # or similar
```

---

### Step 2: Access Production Django Admin

1. Go to: **https://numscoil.ie/admin/**

2. Log in with your superuser credentials

3. Navigate to: **Schools → Schools**

---

### Step 3: Filter Schools That Received Initial Email

**Option A: If you have `initial_email_sent` field populated**
- Click the filter: **"Email status"** → **"Emailed"**
- This shows schools that received the initial outreach

**Option B: If field is not populated (more likely)**
- You'll need to select schools manually OR
- Use the "Select All" option if you want to send to everyone in the database

---

### Step 4: Select Schools for Follow-Up

1. Check the box at the top to **"Select all X schools"**
   - OR manually select specific schools

2. **RECOMMENDED**: Start with a TEST first
   - Select just 1-2 schools for testing
   - Verify the email looks correct
   - Then proceed with full send

---

### Step 5: Choose the Email Action

1. From the **"Actions"** dropdown at the top, select:
   **"Send email to selected schools"**

2. Click **"Go"**

---

### Step 6: Configure the Follow-Up Email

You'll see the email composition form. Fill it out as follows:

**Email Type**:
```
Follow-up
```

**Subject**:
```
Final reminder: 4 free NumScoil places - offer expires 31 Jan
```

**Use template**:
```
☑ CHECKED (this will use the follow_up.html and follow_up.txt templates)
```

**Custom message**:
```
(Leave blank - not needed when using template)
```

**Prefer secondary contact**:
```
☑ CHECKED (sends to maths teachers when available, otherwise principals)
```

**Send test**:
```
☑ CHECKED (for your first send to test the email)
Then UNCHECKED for the actual bulk send
```

---

### Step 7: Send Test Email First

1. With **"Send test"** checked, click **"Send Email"**

2. Check your email inbox (admin@numscoil.ie)

3. Verify:
   - ✅ Subject line is correct
   - ✅ Email formatting looks good (HTML version)
   - ✅ All links work
   - ✅ Deadline date (Jan 31) is mentioned
   - ✅ From address is admin@numscoil.ie

---

### Step 8: Send to All Schools

Once test looks good:

1. Go back to **Schools → Schools**

2. Select all schools that should receive follow-up (or filter appropriately)

3. Choose **"Send email to selected schools"** action again

4. Fill out the form **EXACTLY THE SAME** but:
   - **Send test**: ☐ UNCHECKED

5. Click **"Send Email"**

6. You'll see a success message like:
   ```
   Successfully sent 105 email(s). 0 email(s) failed.
   ```

---

### Step 9: Monitor Results

After sending, you can monitor results in:

1. **Django Admin → Email Logs**
   - Shows all sent emails with status (sent/failed)
   - Timestamps
   - Recipients

2. **SendGrid Dashboard**
   - Login at: https://app.sendgrid.com/
   - Go to: **Email Activity**
   - Monitor: Delivered, Opens, Clicks, Bounces

---

## 🎯 Expected Results

Based on your initial campaign performance:

- **Delivery Rate**: ~35% (37 out of 105)
  - Expect: ~37 delivered out of 105 sent

- **Open Rate**: ~67.6% (of delivered)
  - Expect: ~25 opens

- **Response Rate**: Target 5-10% (of opened)
  - Expect: 1-3 responses

---

## ⚠️ Important Notes

### DO NOT:
- ❌ Send multiple follow-ups to the same schools within 24 hours
- ❌ Send after the Jan 31 deadline (makes you look disorganized)
- ❌ Skip the test email (always test first!)

### DO:
- ✅ Send between 9am-5pm on a weekday (Monday-Friday)
- ✅ Monitor SendGrid for bounces and update email addresses
- ✅ Respond quickly to any replies (within 2 hours if possible)
- ✅ Track responses in Django admin (mark schools as "responded")

---

## 🕐 Best Time to Send

**RECOMMENDED SEND TIMES**:

1. **Monday, Jan 27 at 10:00 AM** (Best)
   - Start of work week
   - Principals check email in morning
   - 4 days before deadline (creates urgency)

2. **Today (Saturday, Jan 24) at 2:00 PM** (Acceptable)
   - Weekend = less inbox competition
   - BUT: Many principals don't check email on weekends

---

## 📊 Tracking Responses

When schools respond, update Django admin:

1. Go to that school's record

2. Set:
   - `response_received` = ☑ True
   - `response_date` = (today's date)
   - `interested` = ☑ True (if they want codes)

3. Add notes in the `notes` field about their response

---

## 🆘 Troubleshooting

### "Template not found" error:
- Verify files are in: `schools/templates/schools/emails/`
- Check file names: `follow_up.html` and `follow_up.txt`
- Restart Django server: `sudo systemctl restart gunicorn`

### High bounce rate (>20%):
- Many school emails are outdated
- Check SendGrid for specific bounce reasons
- Update email addresses in database

### No emails sending:
- Check SendGrid API key is valid
- Verify `EMAIL_HOST_PASSWORD` in production `.env`
- Check Django logs: `/var/log/gunicorn/error.log`

### Emails going to spam:
- Warm up: Send to small batches first (10-20 at a time)
- Check SPF/DKIM records for numscoil.ie domain
- Ask recipients to whitelist admin@numscoil.ie

---

## 📞 Need Help?

If you encounter issues:

1. Check Django admin Email Logs for error messages
2. Check SendGrid Activity Feed for delivery status
3. Check server logs for errors
4. Contact me for assistance

---

**Good luck with your follow-up campaign! 🚀**

*Remember: The deadline is Jan 31 - only 7 days away. Send ASAP!*