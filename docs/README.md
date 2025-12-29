# 🧮 NumScoil (Leaving Cert AI Tutor)

NumScoil is an interactive web-based tutor for Leaving Certificate Honours Maths students.
It provides topic-based questions, AI hints, solutions, and summary notes — all powered by Django and OpenAI.

---

## 📚 Documentation Index

### Getting Started
- **[PythonAnywhere Deployment](PYTHONANYWHERE_DEPLOYMENT.md)** - Complete production deployment guide
- **[Database Sync Manual](DATABASE_SYNC_MANUAL.md)** - Sync local changes to production
- **[Import/Export Commands](IMPORT_EXPORT_COMMANDS.md)** - All data import/export commands

### Features & Systems
- **[Flashcard System](FLASHCARD_FEATURE_BRIEFING.md)** - Flashcard feature overview and usage
- **[Homework System](HOMEWORK_SYSTEM_GUIDE.md)** - Teacher-student homework assignments
- **[Exam Papers](EXAM_PAPERS_IMPLEMENTATION.md)** - Exam paper system guide
- **[Exam Papers Workflow](EXAM_PAPERS_WORKFLOW.md)** - Workflow for adding exam content
- **[Marking Schemes](MARKING_SCHEMES_GUIDE.md)** - Marking scheme integration
- **[Revision App](REVISION_APP_DEPLOYMENT.md)** - Revision materials deployment

### Setup & Configuration
- **[Cloudflare Setup](CLOUDFLARE_SETUP_GUIDE.md)** - CDN and SSL configuration
- **[Email Contact Setup](EMAIL_CONTACT_SETUP.md)** - Contact form email configuration
- **[PDF Resources Setup](PDF_RESOURCES_SETUP.md)** - PDF resource management
- **[Daily Logout Setup](DAILY_LOGOUT_SETUP.md)** - Auto-logout configuration
- **[Daily Report Usage](DAILY_REPORT_USAGE.md)** - Student progress reports

### Development
- **[Manim Specifications](MANIM_SPECIFICATIONS.md)** - Animation specifications
- **[Exam Import Guide](EXAM_IMPORT_GUIDE.md)** - Importing exam questions
- **[Deployment Steps](DEPLOYMENT_STEPS.md)** - Detailed deployment process

---

## 🚀 Features

- Interactive question-based quizzes with instant AI feedback
- Step-by-step worked solutions using LaTeX rendering
- Topic summaries and notes integrated with retrieval-augmented generation (RAG)
- Student login, progress tracking, and performance reports
- Integrated Info-Bot for topic-specific help
- Admin dashboard for managing lessons, topics, and content
- Flashcard system for quick revision
- Homework assignment system for teachers
- Full exam paper practice mode

---

## ⚙️ Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/morgan360/lcstats.git
cd lcstats
