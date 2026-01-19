# Teacher Documentation Package - Summary

This package contains all documentation needed to onboard a new teacher to NumScoil.

---

## 📦 What's Included

### 1. **TEACHER_USER_GUIDE.md** (Comprehensive Manual)
**File:** `/Users/morgan/lcstats/docs/TEACHER_USER_GUIDE.md`
**Purpose:** Complete reference guide for all teacher features
**Length:** ~580 lines, comprehensive coverage
**Best for:** Reference, detailed instructions, troubleshooting

**Contents:**
- Getting Started with NumScoil
- Accessing Teacher Dashboard
- Managing Classes
- Creating Homework Assignments (step-by-step)
- Monitoring Student Progress
- Understanding Content Types (Sections, Exam Questions, QuickFlicks, Flashcards)
- Tips for Success
- Common Workflows (3 scenarios)
- FAQ (10 questions)
- Quick Reference Tables

---

### 2. **TEACHER_QUICKSTART_GUIDE.md** (10-Minute Setup)
**File:** `/Users/morgan/lcstats/docs/TEACHER_QUICKSTART_GUIDE.md`
**Purpose:** Get teachers up and running fast
**Length:** ~180 lines, action-focused
**Best for:** First-time setup, quick reference

**Contents:**
- Login steps
- **Student registration code explanation** (auto-enrollment)
- Creating first homework assignment (5 minutes)
- Checking student progress (30 seconds)
- Quick tips and troubleshooting
- Important links and reference tables

**Key Feature:** Emphasizes that students are **automatically enrolled** when they register with the teacher's registration code.

---

### 3. **TEACHER_WELCOME_EMAIL_TEMPLATE.md** (Email to Send)
**File:** `/Users/morgan/lcstats/docs/TEACHER_WELCOME_EMAIL_TEMPLATE.md`
**Purpose:** Ready-to-customize welcome email for new teachers
**Length:** ~150 lines, email-ready format
**Best for:** First contact with new teacher

**Contents:**
- Login credentials placeholders
- **Student registration code** (to share with students)
- Pre-written message for teachers to send to students
- Attachment list (guides)
- Support contact information
- Action plan for first week

**How to use:**
1. Copy the email content
2. Replace `[INSERT_USERNAME]`, `[INSERT_PASSWORD]`, `[INSERT_REGISTRATION_CODE]`
3. Add your support contact details
4. Attach the Quick Start and User Guides
5. Send!

---

### 4. **TEACHER_ONE_PAGE_GUIDE.md** (Print-Ready Reference)
**File:** `/Users/morgan/lcstats/docs/TEACHER_ONE_PAGE_GUIDE.md`
**Purpose:** Single-page quick reference sheet
**Length:** ~80 lines, concise and tabular
**Best for:** Printing and keeping at desk

**Contents:**
- All essential links
- Student registration explanation
- 5-minute homework creation steps
- Progress check symbols
- Task types table
- Pro tips
- Quick troubleshooting table

**How to use:** Print and give to teacher as a desk reference

---

## 🎯 How to Use This Package

### For Onboarding a New Teacher:

**Step 1: Send Welcome Email**
- Use `TEACHER_WELCOME_EMAIL_TEMPLATE.md`
- Fill in credentials and registration code
- Attach Quick Start Guide and User Guide

**Step 2: Teacher Reviews Guides**
- They start with **Quick Start Guide** (10 min)
- Refer to **User Guide** for detailed questions

**Step 3: Optional - Print Reference Sheet**
- Print `TEACHER_ONE_PAGE_GUIDE.md` for their desk

---

## 🔑 Key Information About Student Registration

All guides emphasize the **automatic class enrollment** feature:

### How It Works:
1. **You provide** a registration code to the teacher (created via Admin)
2. **Teacher shares** this code with students
3. **Students sign up** at https://www.numscoil.ie/students/signup/
4. **Students enter** the registration code during signup
5. **System automatically** adds students to the teacher's class

### Registration Code Creation:
**Admin Panel → Students → Registration Codes → Add Registration Code**
- **Code Type:** `student`
- **Linked Class:** Select the teacher's class
- **Max Uses:** 0 (unlimited) or set a specific number
- **Code:** Auto-generated (e.g., `STU-ABC123`)

When students register with this code, they're instantly enrolled in the linked class!

---

## 📋 Quick Reference: What Teachers Can Do

### Class Management
✅ View all students in their classes
✅ Monitor student enrollment (automatic via registration codes)
✅ View class-level reports

### Homework System
✅ Create assignments with multiple task types
✅ Assign to entire classes or individual students
✅ Set due dates (required)
✅ Use draft mode for preparation
✅ Edit published assignments

### Progress Tracking
✅ See task-by-task completion
✅ View submission status (on-time vs. late)
✅ Generate weekly reports (print-ready)
✅ Automatic task completion detection
✅ Student-by-student progress matrix

### Content Types Teachers Can Assign
✅ **Topic Sections** - Practice questions with AI feedback
✅ **Exam Questions** - Past Leaving Cert papers
✅ **QuickFlicks** - Tutorial videos and applets
✅ **Flashcard Sets** - Spaced repetition practice

---

## 🌐 Important URLs (All Included in Guides)

| Purpose | URL |
|---------|-----|
| Main Site | https://www.numscoil.ie |
| Login | https://www.numscoil.ie/students/login/ |
| Student Signup | https://www.numscoil.ie/students/signup/ |
| Teacher Dashboard | https://www.numscoil.ie/homework/teacher/ |
| Admin Panel | https://www.numscoil.ie/admin/ |

---

## ✅ Checklist: Onboarding a New Teacher & School

- [ ] Create teacher account (User with `is_staff=True`)
- [ ] Create TeacherProfile in Admin → Homework → Teacher Profiles
- [ ] Create TeacherClass in Admin → Homework → Classes
- [ ] Create RegistrationCode in Admin → Students → Registration Codes
  - Code Type: `student`
  - Link to the TeacherClass
  - Set max_uses (0 = unlimited)
- [ ] Note the auto-generated registration code
- [ ] Customize welcome email template with:
  - [ ] Teacher username
  - [ ] Teacher password
  - [ ] Student registration code
  - [ ] Support contact details
- [ ] Attach guides to email:
  - [ ] TEACHER_QUICKSTART_GUIDE.md
  - [ ] TEACHER_USER_GUIDE.md
- [ ] Send welcome email to teacher
- [ ] (Optional) Print TEACHER_ONE_PAGE_GUIDE.md for teacher's desk

---

## 💡 Pro Tips for Administrators

### Registration Code Best Practices
- **One code per class** - Makes tracking easier
- **Unlimited uses** - Set max_uses to 0 for simplicity
- **Descriptive naming** - Admin can add notes to codes
- **Auto-enrollment** - Students instantly join the linked class

### Teacher Onboarding Best Practices
- **Send credentials separately** - Email password, share registration code via secure channel
- **Start small** - Encourage first assignment with 2-3 tasks
- **Follow up** - Check in after first week to answer questions
- **Share success stories** - Show examples from other teachers

### Common Teacher Questions (Prepare Answers)
1. "What if a student loses the registration code?" → Resend it or create a new one
2. "Can I change the code later?" → Yes, create a new code and disable the old one
3. "What if a student registers with the wrong code?" → Manually add them to correct class
4. "How do I remove a student from my class?" → Admin → Homework → Classes → Edit class
5. "Can I have multiple classes?" → Yes! Create multiple classes, each with its own code

---

## 📊 Success Metrics to Track

After onboarding, monitor:
- ✅ Student registration rate (within first week)
- ✅ First homework assignment created (within 2 weeks)
- ✅ Student homework completion rates
- ✅ Teacher login frequency
- ✅ Number of assignments created per month

---

## 🆘 Support Resources for Teachers

**Included in all guides:**
- Quick troubleshooting tables
- FAQ sections
- Step-by-step instructions with examples
- Reference tables and symbols
- Contact information placeholders

**Escalation path:**
1. Teacher checks Quick Start or User Guide
2. Teacher contacts school administrator
3. Administrator contacts you (if needed)

---

## 🎉 You're Ready!

This package provides everything needed to successfully onboard a new teacher and their students to NumScoil. The emphasis on **automatic class enrollment via registration codes** makes the process smooth and reduces manual work.

**Next Steps:**
1. Create the teacher account and registration code
2. Customize and send the welcome email
3. Support teacher through first week
4. Celebrate when students start using NumScoil! 🚀

---

*Documentation created: January 2025*
*For: NumScoil Teacher Onboarding*