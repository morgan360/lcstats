# Homework System - Complete Guide

## Overview
A comprehensive homework management system has been added to LCAI Maths. This allows teachers to create classes, assign homework with multiple tasks (Sections, Exam Questions, and QuickKicks), and track student progress.

## Features Implemented

### For Teachers
- **Teacher Profiles**: Extended user model for staff members
- **Class Management**: Create and manage classes with enrolled students
- **Homework Assignments**: Create assignments for specific topics with:
  - Multiple task types (Sections, Exam Questions, QuickKicks)
  - Due dates (required)
  - Assignment to entire classes or individual students
  - Draft mode before publishing
- **Progress Tracking**: View detailed progress for each assignment showing:
  - Which tasks each student has completed
  - Submission status (on-time/late)
  - Completion percentages

### For Students
- **Homework Dashboard**: View all active and completed homework
  - Clear indicators for overdue assignments
  - Progress bars showing completion status
  - Due date warnings
- **Assignment Detail View**: See all tasks with:
  - Checkbox to mark tasks complete
  - Direct links to content (sections/questions/videos)
  - Instructions for each task
  - Submit button when all tasks are complete
- **Student Dashboard Integration**: Homepage shows homework summary with:
  - Overdue assignments highlighted
  - Upcoming assignments listed
  - Quick link to full homework dashboard

## Database Models

### TeacherProfile
- Links to User (staff only)
- Display name and contact email
- Active status

### TeacherClass
- Managed by a teacher
- Contains many students
- Active/inactive status

### HomeworkAssignment
- Created by a teacher for a specific Topic
- Can be assigned to:
  - One or more classes
  - Individual students (or both)
- Has a due date (required)
- Can be draft or published

### HomeworkTask
- Belongs to an assignment
- References one of three content types:
  - Section (from interactive_lessons)
  - ExamQuestion (from exam_papers)
  - QuickKick (video/applet)
- Can be required or optional
- Has display order

### StudentHomeworkProgress
- Tracks completion of individual tasks by students
- Records completion timestamp
- Optional notes field

### HomeworkSubmission
- Records when student submits completed homework
- Auto-detects late submissions
- Supports teacher feedback

## Admin Interface

All models are accessible through Django Admin (`/admin/`) with:
- **Comprehensive filtering**: By teacher, topic, due date, status
- **Inline task editing**: Add tasks directly when creating assignments
- **Permission controls**: Teachers only see their own content
- **Progress summaries**: View completion rates at a glance
- **Colored status badges**: Visual indicators for draft/active/overdue

## URL Structure

- `/homework/` - Student homework dashboard
- `/homework/assignment/<id>/` - Assignment detail with tasks
- `/homework/teacher/` - Teacher dashboard
- `/homework/teacher/class/<id>/` - Class detail
- `/homework/teacher/assignment/<id>/progress/` - Assignment progress tracking

## How to Use

### For Teachers (via Admin)

1. **Create Teacher Profile** (Admin → Homework → Teacher Profiles)
   - Link to your staff user account
   - Set display name

2. **Create a Class** (Admin → Homework → Classes)
   - Name your class
   - Add students from the dropdown

3. **Create Homework Assignment** (Admin → Homework → Homework Assignments)
   - Select topic and set title
   - Add description/instructions
   - Set due date
   - Assign to classes and/or individual students
   - Add tasks inline:
     - Choose task type (Section/Exam Question/QuickKick)
     - Select the specific content
     - Mark as required/optional
     - Add specific instructions
   - Publish when ready

4. **Monitor Progress** (Teacher Dashboard or Admin)
   - View submission rates
   - See per-student task completion
   - Add feedback to submissions

### For Students

1. **Check Homework** (Click "Homework" in navigation)
   - See all active assignments
   - Identify overdue assignments (red)
   - Check upcoming deadlines

2. **Complete Tasks** (Click on assignment)
   - Click links to access each task
   - Check off tasks as you complete them
   - Submit when all tasks are done

3. **Dashboard Reminder** (Student Dashboard shows homework summary on login)

## Navigation

- **Students**: "Homework" link in main navigation (when logged in)
- **Teachers**: "Homework" link shows student view; access teacher dashboard via `/homework/teacher/`
- **Dashboard**: Student homepage now shows homework summary

## Key Features

✅ **Teacher-Class System**: Each teacher manages their own classes
✅ **Flexible Assignment**: Assign to classes, individuals, or both
✅ **Multiple Content Types**: Mix sections, exam questions, and videos in one assignment
✅ **Real-time Progress**: Students check off tasks; teachers see updates
✅ **Late Detection**: Automatic flagging of late submissions
✅ **Due Date Tracking**: Clear warnings for upcoming and overdue work
✅ **Student Dashboard Integration**: Homework visible immediately on login
✅ **Mobile-Friendly**: Responsive design works on all devices

## Technical Notes

- Migrations have been run successfully
- All models registered in admin
- URLs integrated into main urlconf
- Navigation updated in base template
- Student dashboard enhanced with homework data

## Next Steps (Optional Enhancements)

Consider adding:
- Email notifications for new assignments
- Automatic reminders for due dates
- Grade/score tracking for assignments
- Export progress reports to CSV
- Student comments/questions on tasks
- Bulk assignment creation
- Assignment templates

## Support

For issues or questions about the homework system, check:
- Admin interface for full CRUD operations
- Teacher dashboard at `/homework/teacher/`
- Models in `homework/models.py` for reference
