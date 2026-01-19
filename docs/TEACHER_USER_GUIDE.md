# NumScoil Teacher User Guide

Welcome to NumScoil! This guide will help you get started with managing your classes and assigning homework to your students.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Accessing Your Teacher Dashboard](#accessing-your-teacher-dashboard)
3. [Managing Your Classes](#managing-your-classes)
4. [Creating Homework Assignments](#creating-homework-assignments)
5. [Monitoring Student Progress](#monitoring-student-progress)
6. [Understanding the Content Types](#understanding-the-content-types)
7. [Tips for Success](#tips-for-success)
8. [Support](#support)

---

## Getting Started

### What is NumScoil?

NumScoil is an AI-powered interactive tutor designed specifically for Leaving Certificate Honours Maths students. The platform provides:

- **Interactive practice questions** with instant AI feedback
- **Step-by-step worked solutions** with LaTeX rendering
- **Past exam papers** with marking schemes
- **Flashcard sets** for active recall practice
- **QuickFlicks** - short video tutorials and interactive applets
- **AI-powered hints** and help
- **Progress tracking** for students

### Your Teacher Account

Your account has been set up with teacher privileges, giving you access to:

- **Class Management** - Create and manage classes of students
- **Homework Assignment System** - Assign specific tasks to students
- **Progress Tracking** - Monitor completion rates and student activity
- **Weekly Reports** - Print-friendly reports for record keeping

---

## Accessing Your Teacher Dashboard

### Logging In

1. Go to **https://www.numscoil.ie**
2. Click **"Login"** in the top navigation
3. Enter your username and password
4. You'll be redirected to the main student interface

### Finding Your Teacher Dashboard

After logging in, access your teacher dashboard by:

**Option 1: Direct URL**
- Go to: **https://www.numscoil.ie/homework/teacher/**
- Bookmark this page for quick access

**Option 2: Admin Interface** (if you have admin access)
- Go to: **https://www.numscoil.ie/admin/**
- Navigate to the Homework section

Your teacher dashboard shows:
- All your classes with student counts
- Recent homework assignments
- Submission statistics
- Quick links to create new assignments

---

## Managing Your Classes

### Creating a New Class

Classes help you organize students into groups (e.g., "6th Year Maths A", "LC Higher Level 2024-25").

**Via Django Admin:**

1. Go to **https://www.numscoil.ie/admin/**
2. Click **"Homework"** → **"Classes"**
3. Click **"Add Class"** (green button, top right)
4. Fill in the details:
   - **Teacher**: Select your teacher profile
   - **Name**: Give your class a descriptive name (e.g., "6th Year Group 1")
   - **Description**: Optional - add details like timetable, room number, etc.
   - **Students**: Select students from the dropdown (hold Ctrl/Cmd to select multiple)
   - **Is active**: Check this box (unchecked classes are hidden)
5. Click **"Save"**

### Viewing Your Classes

**From Teacher Dashboard:**
- Each class card shows:
  - Class name
  - Number of students enrolled
  - Link to view class details

**From Admin Interface:**
- Go to **Homework** → **Classes**
- Filter by your name to see only your classes
- Click any class name to edit

### Adding/Removing Students

1. Go to **Admin** → **Homework** → **Classes**
2. Click on the class name
3. Scroll to the **"Students"** field
4. Use the dropdown to add students or remove them
5. Click **"Save"**

**Tip:** Students must already have user accounts before you can add them to a class. Contact your administrator if you need student accounts created.

---

## Creating Homework Assignments

Homework assignments can include multiple types of tasks. Students will see all tasks on one page with direct links to complete each one.

### Step-by-Step: Creating an Assignment

**Via Django Admin:**

1. Go to **https://www.numscoil.ie/admin/**
2. Click **"Homework"** → **"Homework Assignments"**
3. Click **"Add Homework Assignment"** (green button, top right)

### Assignment Details

Fill in these fields:

#### Basic Information

- **Teacher**: Select your teacher profile (should auto-select)
- **Topic**: Choose the maths topic this assignment covers (e.g., "Differentiation", "Trigonometry")
- **Title**: Give your assignment a clear name (e.g., "Differentiation Week 1", "Trig Practice - Radians")
- **Description**: Add instructions for students. Examples:
  - "Complete all tasks by Friday's class"
  - "Focus on understanding the chain rule - use hints if needed"
  - "This homework prepares you for next week's test"

#### Assignment Targets

Choose who receives this homework:

- **Assigned Classes**: Select entire classes (e.g., "6th Year Group 1")
  - Hold Ctrl/Cmd to select multiple classes
- **Assigned Students**: Optionally add individual students
  - Useful for catch-up work or differentiation

**Note:** You can assign to classes, individual students, or both!

#### Timing

- **Assigned Date**: Defaults to today (when homework is visible to students)
- **Due Date**: **REQUIRED** - Select the deadline
  - Students will see warnings as the due date approaches
  - Late submissions are automatically flagged

#### Status

- **Is Published**: Check this box to make the assignment visible to students
  - Leave unchecked to save as a draft
  - You can edit drafts and publish later

### Adding Tasks to Your Assignment

This is where you specify what students need to do. Scroll down to the **"Homework Tasks"** section at the bottom of the page.

Click **"Add another Homework Task"** to add each task:

#### Task Fields

1. **Task Type**: Choose one:
   - **Topic Section** - Practice questions from a specific section
   - **Exam Question** - Practice a specific past exam question
   - **QuickFlicks Video/Applet** - Watch a video or use an interactive tool
   - **Flashcard Set** - Study flashcards for active recall

2. **Content Selection**: Based on the task type selected above, choose the specific content:
   - For **Section**: Select from dropdown (e.g., "The Chain Rule")
   - For **Exam Question**: Select a past paper question
   - For **QuickFlicks**: Choose a video/applet
   - For **Flashcard**: Select a flashcard set

3. **Instructions**: Add task-specific guidance (optional):
   - "Complete all 10 questions in this section"
   - "Watch this video before attempting the questions"
   - "Focus on questions (a) and (c)"

4. **Is Required**: Checked by default
   - Uncheck for optional/bonus tasks

5. **Order**: Number to control task display order
   - Use 1, 2, 3, etc. to organize tasks logically

#### Example Assignment

**Title:** "Differentiation - Chain Rule Introduction"
**Topic:** Differentiation
**Due Date:** Friday, 5:00 PM
**Assigned Classes:** 6th Year Group 1

**Tasks:**
1. **QuickFlicks** - "Chain Rule Explained" (Order: 1)
   - Instructions: "Watch this 5-minute introduction first"
2. **Section** - "The Chain Rule" (Order: 2)
   - Instructions: "Complete at least 5 questions - use hints if stuck"
3. **Flashcard Set** - "Differentiation Rules" (Order: 3)
   - Instructions: "Review these before Friday's class"
   - Is Required: **Unchecked** (optional)

### Publishing Your Assignment

- Check **"Is Published"**
- Click **"Save"** at the bottom
- Students will now see the assignment in their homework dashboard

---

## Monitoring Student Progress

NumScoil gives you several ways to track student work:

### 1. Teacher Dashboard Overview

From `/homework/teacher/`:

- See all your assignments with submission counts
- View submission percentages at a glance
- Click any assignment to see detailed progress

### 2. Assignment Progress View

Click **"View Progress"** on any assignment to see:

- **Student-by-Student Breakdown**:
  - Each student's name
  - Which tasks they've completed (✓ or ○)
  - Overall completion percentage
  - Submission status and timestamp
  - Late submission indicators

- **Task Completion Matrix**:
  - Rows = Students
  - Columns = Tasks
  - Quickly identify who's falling behind

### 3. Class Homework Report

From your teacher dashboard, click on a class name to access:

**`/homework/teacher/class-report/<class-id>/`**

This shows:
- All homework assigned to that class
- Completion status for each student
- ✓ = All tasks complete
- ✗ = Some tasks complete
- (blank) = Not started

### 4. Weekly Reports (Print-Friendly)

Perfect for record-keeping and parent meetings!

**Class Weekly Report:**
- URL: `/homework/class-report/weekly/<class-id>/`
- Shows all homework due this week
- Student initials across the top
- Homework assignments down the left
- Print-ready format

**Individual Student Weekly Report:**
- URL: `/homework/student-report/weekly/<student-id>/`
- Shows one student's homework for the week
- Detailed task-by-task breakdown
- Perfect for parent meetings or check-ins

### Understanding Task Auto-Completion

NumScoil **automatically** marks tasks as complete when students:

- **Section Tasks**: Submit answers to questions in that section
- **Exam Question Tasks**: Attempt the exam question
- **QuickFlicks Tasks**: View the video/applet
- **Flashcard Tasks**: Practice flashcards from that set

Students can also manually check off tasks, but auto-completion ensures accurate tracking even if they forget!

---

## Understanding the Content Types

### Topic Sections

These are practice question sets organized by maths topic and skill level.

**Example Sections:**
- "The Chain Rule" (Differentiation)
- "Radians and Arc Length" (Trigonometry)
- "Hypothesis Testing - Mean" (Statistics)

**What students do:**
- Work through 8-15 practice questions
- Get instant AI feedback on answers
- Access hints (with small penalty)
- View full solutions (with penalty)

**Best for:** Building fluency with a specific skill

### Exam Questions

These are actual past Leaving Certificate exam questions.

**What students do:**
- Practice questions from real past papers
- See marking schemes and solutions
- Track progress on exam-style questions

**Best for:** Exam preparation and applying skills in context

### QuickFlicks (Videos/Applets)

Short instructional videos and interactive demonstrations.

**What students do:**
- Watch 3-10 minute explanations
- Use interactive tools to visualize concepts
- Viewing is automatically tracked

**Best for:** Introducing new concepts or reviewing before practice

### Flashcard Sets

Active recall practice using spaced repetition.

**What students do:**
- Test themselves on definitions, formulas, and procedures
- Progress through: New → Learning → Know → Retired
- Self-assess their knowledge

**Best for:** Memorization and quick recall (formulas, definitions)

---

## Tips for Success

### Creating Effective Homework

✅ **Mix task types**: Combine videos, practice, and flashcards for variety

✅ **Start with QuickFlicks**: Assign videos first to introduce new concepts

✅ **Be specific in instructions**: Tell students how many questions to complete or what to focus on

✅ **Set realistic deadlines**: Give students enough time to complete all tasks

✅ **Use the topic system**: Keep assignments focused on one topic when possible

### Managing Your Classes

✅ **Create multiple classes** if you teach different levels or time slots

✅ **Use descriptive class names**: Include year, level, or period (e.g., "6th Year HL Period 2")

✅ **Keep classes updated**: Remove students who drop or transfer

### Tracking Progress

✅ **Check progress regularly**: Look at completion rates mid-week to identify struggling students

✅ **Use weekly reports**: Print reports for your records and student conferences

✅ **Follow up on late submissions**: The system automatically flags late work

✅ **Review the task completion matrix**: Spot patterns (e.g., everyone struggling with task 3)

### Working with Students

✅ **Encourage hint usage**: Hints help learning (even with small penalties)

✅ **Remind about auto-completion**: Students don't always need to manually check tasks

✅ **Use draft mode**: Prepare assignments in advance and publish when ready

✅ **Assign to individuals**: Give extra practice to students who need it

---

## Common Workflows

### Scenario 1: Weekly Homework Routine

**Monday:**
1. Create new assignment for current topic
2. Add 3-4 tasks (video + section + flashcards)
3. Set due date for Friday
4. Publish to your classes

**Wednesday:**
- Check progress view
- Identify students who haven't started
- Reminder in class or individual follow-up

**Friday:**
- Review final submissions
- Print weekly class report for records
- Note late submissions

**Weekend/Monday:**
- Review next week's topic
- Prepare next assignment

### Scenario 2: Exam Preparation

**2 Weeks Before Mock Exam:**
1. Create assignment: "Mock Exam Preparation - Differentiation"
2. Add tasks:
   - Flashcard review (all differentiation rules)
   - 3-4 topic sections for practice
   - 2-3 past exam questions
3. Set longer deadline (1 week)
4. Assign to all exam classes

**Monitor progress** and identify weak areas for review lessons

### Scenario 3: Differentiated Instruction

**For advanced students:**
- Create individual assignment with challenging exam questions
- Set as optional (uncheck "Is Required" on tasks)

**For students needing support:**
- Create targeted assignment focusing on one skill
- Assign just to those students
- Include QuickFlicks video as first task
- Choose easier section with more hints available

---

## Frequently Asked Questions

### Can I edit a published assignment?

Yes! Go to **Admin** → **Homework** → **Homework Assignments**, find your assignment, and edit it. Changes are immediately visible to students.

**Warning:** If you remove tasks that students have already completed, their progress on those tasks will be lost.

### Can I assign the same homework to multiple classes?

Yes! When creating an assignment, select multiple classes in the **"Assigned Classes"** field (hold Ctrl/Cmd to select multiple).

### What happens if a student joins my class after I've assigned homework?

**For new assignments:** The student will automatically see any new homework you publish.

**For existing assignments:** You'll need to manually add the student to the assignment:
1. Go to **Admin** → **Homework** → **Homework Assignments**
2. Find the assignment
3. Add the student to **"Assigned Students"**

**Alternative:** Re-save the assignment with the class selected, and the system will create progress records for new students.

### How do students submit homework?

When students complete all required tasks, they click a **"Submit"** button on the assignment page. This creates a submission record visible to you.

**Note:** Students can complete tasks even after the due date, but submissions will be marked as late.

### Can I see individual question answers?

The homework system tracks task completion, not individual answers. To see detailed question-by-question performance, use the admin interface:

- **Admin** → **Students** → **Question Attempts**
- Filter by student and date range

### Can students see each other's progress?

No. Students only see their own homework and progress. Only you (the teacher) can see class-wide progress.

### What if a student claims they completed a task but it's not showing?

1. Check the **Assignment Progress** view
2. Auto-completion might be delayed - ask the student to refresh their page
3. Verify the student actually attempted the correct content (e.g., right section)
4. Students can manually check off tasks if auto-completion fails

### Can I reuse assignments?

Not directly through the interface, but you can:
1. Open an old assignment in the admin
2. Manually copy the task details
3. Create a new assignment with the same tasks
4. Change the due date and assigned classes

**Tip:** Keep a document with your standard assignment templates for quick reference.

### How do I remove a student from all my classes?

1. Go to **Admin** → **Homework** → **Classes**
2. Open each class
3. Remove the student from the **Students** field
4. Save each class

**Note:** This doesn't delete the student's account, just removes them from your classes.

---

## Support

### Need Help?

If you encounter any issues or have questions:

1. **Check this guide first** - Most common questions are answered here
2. **Contact your school administrator** - They can help with account issues, adding students, etc.
3. **Email support**: [Your support email will be provided by your administrator]

### Reporting a Problem

When reporting an issue, please include:
- Your username
- Which class or assignment you're working with
- What you were trying to do
- What happened instead
- Screenshot if possible

### Feature Requests

We're always improving NumScoil! If you have suggestions for new features or improvements to the homework system, please let us know.

---

## Quick Reference

### Important URLs

| Page | URL |
|------|-----|
| Main site | https://www.numscoil.ie |
| Login | https://www.numscoil.ie/students/login/ |
| Teacher Dashboard | https://www.numscoil.ie/homework/teacher/ |
| Admin Interface | https://www.numscoil.ie/admin/ |

### Keyboard Shortcuts (Admin Interface)

- **Ctrl/Cmd + S**: Save
- **Ctrl/Cmd + K**: Jump to search
- **Alt + S**: Save and continue editing

### Task Types Summary

| Task Type | What Students Do | Auto-Completion Trigger |
|-----------|-----------------|------------------------|
| Topic Section | Answer practice questions | Submit any answer in section |
| Exam Question | Attempt past exam question | Submit attempt on that question |
| QuickFlicks | Watch video or use applet | View tracked automatically |
| Flashcard Set | Practice flashcards | Attempt any card in set |

### Progress Indicators

| Symbol | Meaning |
|--------|---------|
| ✓ | Task completed |
| ○ | Task not completed |
| ✗ | Partially complete (in some views) |
| 🔴 (Red) | Assignment overdue |
| "LATE" | Submission after due date |

---

**Welcome to NumScoil! We hope this guide helps you get the most out of the homework system. Your students are fortunate to have access to this powerful learning tool, and your guidance will help them succeed.**

**Good luck!**

---

*This guide was created for NumScoil Teacher Edition - Version 1.0*
*Last updated: January 2026*