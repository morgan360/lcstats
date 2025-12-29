# Daily Student Activity Report

This document explains how to use the daily student activity report feature.

## Overview

The daily student report summarizes topics and questions completed by all students in a specified time period. You can exclude specific users (like yourself) from the report.

**Two ways to generate reports:**
1. **Django Admin Actions** (Easiest - via web interface)
2. **Management Command** (For automation/scheduling)

## Method 1: Using Django Admin (Recommended)

The easiest way to generate reports is directly from the Django admin interface:

### Steps:

1. **Log in to Django Admin** at `/admin/`
2. **Navigate to Students → Student profiles**
3. **Select the action:**
   - For all students: Leave the checkboxes empty (no students selected)
   - For specific students: Check the boxes next to students you want to include
4. **Choose an action from the dropdown:**
   - `📊 Generate Daily Report (24 hours)` - Last 24 hours
   - `📊 Generate Weekly Report (7 days)` - Last 7 days
5. **Click "Go"**
6. **Download the report** - Your browser will download a `.txt` file

### Features:

- **Automatically excludes you** (the logged-in admin user) from the report
- **Filter by students** - Select specific students to include only their data
- **Instant download** - Report generated as a downloadable text file
- **No configuration needed** - Works immediately after login

### Report Filename:

Downloads are named like: `student_report_1day_20251116.txt` or `student_report_7day_20251116.txt`

---

## Method 2: Using Management Command

### Basic Command

Run a report for the last 24 hours and print to console:

```bash
python manage.py daily_student_report --dry-run
```

### Exclude Yourself from the Report

Replace `YOUR_USERNAME` with your actual username:

```bash
python manage.py daily_student_report --exclude-user YOUR_USERNAME --dry-run
```

### Send Report via Email

```bash
python manage.py daily_student_report --exclude-user YOUR_USERNAME --email your@email.com
```

### Custom Time Period

Generate a report for the last 7 days:

```bash
python manage.py daily_student_report --exclude-user YOUR_USERNAME --days 7 --email your@email.com
```

## Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--exclude-user` | Username to exclude from report | `--exclude-user teacher1` |
| `--email` | Email address to send report to | `--email admin@school.com` |
| `--days` | Number of days to include (default: 1) | `--days 7` |
| `--dry-run` | Preview report without sending email | `--dry-run` |

## Report Contents

The report includes:

### Overall Summary
- Number of active students
- Total question attempts
- Correct answers count
- Overall accuracy percentage
- Unique questions attempted

### Topics Summary
- List of topics worked on
- Attempt count per topic
- Correct answers per topic
- Average score per topic

### Student Breakdown
For each student:
- Name and username
- Number of attempts
- Correct answers and accuracy
- Average score
- Cumulative total score
- Cumulative lessons completed
- Top 5 topics worked on

## Scheduling Daily Reports

### Option 1: Cron (Linux/Mac)

Edit your crontab:
```bash
crontab -e
```

Add a line to run the report daily at 8 AM:
```cron
0 8 * * * cd /home/user/lcstats && /usr/bin/python manage.py daily_student_report --exclude-user YOUR_USERNAME --email your@email.com
```

### Option 2: Task Scheduler (Windows)

1. Open Task Scheduler
2. Create a new task
3. Set trigger: Daily at desired time
4. Set action: Run `python manage.py daily_student_report --exclude-user YOUR_USERNAME --email your@email.com`
5. Set start in: `/home/user/lcstats`

### Option 3: PythonAnywhere Scheduled Tasks

If hosting on PythonAnywhere:

1. Go to Tasks tab
2. Add a new scheduled task
3. Set time (e.g., 08:00 UTC)
4. Command: `cd /home/yourusername/lcstats && python manage.py daily_student_report --exclude-user YOUR_USERNAME --email your@email.com`

## Examples

### Preview today's report excluding yourself:
```bash
python manage.py daily_student_report --exclude-user morgan --dry-run
```

### Send weekly report:
```bash
python manage.py daily_student_report --exclude-user morgan --days 7 --email teacher@school.com
```

### Get help:
```bash
python manage.py daily_student_report --help
```

## Troubleshooting

### Email not sending

1. Check your email settings in `lcstats/settings.py`
2. Verify environment variables in `.env`:
   - `EMAIL_HOST_USER`
   - `EMAIL_HOST_PASSWORD`
3. Test with `--dry-run` first to preview the report

### No data in report

- Verify students have attempted questions in the time period
- Check the date range with `--days` option
- Ensure the excluded user is correct

### Finding your username

Run in Django shell:
```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
User.objects.all().values_list('username', 'email')
```

## Sample Output

```
======================================================================
DAILY STUDENT ACTIVITY REPORT
======================================================================
Period: 2025-11-15 00:00 to 2025-11-16 00:00
Duration: 1 day(s)
Excluded user: teacher1

----------------------------------------------------------------------
OVERALL SUMMARY
----------------------------------------------------------------------
Active Students: 5
Total Attempts: 127
Correct Answers: 98
Overall Accuracy: 77.2%
Unique Questions Attempted: 23

----------------------------------------------------------------------
TOPICS WORKED ON
----------------------------------------------------------------------
Topic                          Attempts   Correct    Avg Score
----------------------------------------------------------------------
Algebra                        45         38         82.3%
Geometry                       32         25         78.1%
Trigonometry                   28         20         71.4%
Calculus                       22         15         68.2%

----------------------------------------------------------------------
STUDENT BREAKDOWN
----------------------------------------------------------------------

John Smith (john.smith)
  Attempts: 35
  Correct: 28 (80.0%)
  Average Score: 82.5%
  Total Score (cumulative): 1250
  Lessons Completed (cumulative): 15
  Topics:
    - Algebra: 15 attempts
    - Geometry: 12 attempts
    - Calculus: 8 attempts
...
```
