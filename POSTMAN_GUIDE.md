# NumScoil API - Postman Collection Guide

## Overview
This Postman collection provides complete API coverage for the NumScoil platform, including authentication, interactive lessons, exam papers, homework, and more.

## Quick Start

### 1. Import the Collection
1. Open Postman
2. Click **Import** button
3. Select `NumScoil_API.postman_collection.json`
4. The collection will appear in your Collections sidebar

### 2. Set Environment Variables
The collection uses these variables:
- `base_url` - Default: `http://localhost:8000` (change for production)
- `csrf_token` - Auto-populated by the "Get CSRF Token" request

### 3. Authentication Flow

**For first-time setup:**
```
1. Run "Get CSRF Token" request
2. Run "Login" request
3. Session cookie is automatically stored
4. All subsequent requests use the session cookie
```

## Collection Structure

### 📁 Authentication
- **Get CSRF Token** - Run this first to get CSRF token for POST requests
- **Signup** - Register new student (requires valid registration code)
- **Login** - Authenticate user (stores session cookie automatically)
- **Logout** - End session

### 📁 Students
- **Dashboard** - View student progress, attempts, and topic performance

### 📁 Interactive Lessons
- **Select Topic** - List all available topics
- **Section List** - Get sections for a topic
- **Section Quiz** - Access quiz interface
- **Submit Answer** - Submit answer for grading
- **Get Hint** - Request hint (-20% penalty)
- **Get Solution** - View solution (-50% penalty)
- **Info Bot (AI Help)** - Ask AI tutor questions (uses RAG + GPT-4o-mini)
- **Topic Exam Questions** - View exam questions by topic
- **Contact Teacher** - Send question to teacher

### 📁 Exam Papers
- **List Papers** - All available exam papers
- **Paper Detail** - Specific paper details
- **Start Paper Attempt** - Begin timed or practice exam
- **Question Interface** - View exam question
- **Submit Answer** - Submit answer (JSON body)
- **Get Solution** - Unlock solution (validates attempts)
- **Complete Attempt** - Finish exam
- **View Results** - See exam results

### 📁 Notes & Knowledge Base
- **Notes Index** - All notes
- **Topic Notes** - Notes filtered by topic
- **Save Info (Search)** - Semantic search using FAISS embeddings

### 📁 Chat
- **Chat Interface** - AI tutor chat

### 📁 Homework
- **Student Dashboard** - View assignments
- **Assignment Detail** - Detailed assignment view
- **Toggle Task Completion** - Mark tasks complete/incomplete
- **Submit Homework** - Submit assignment
- **Snooze Notification** - Snooze homework reminders
- **Teacher Dashboard** - Teacher view (requires permissions)

### 📁 Admin
- **Admin Panel** - Django admin (requires superuser)

## Usage Examples

### Example 1: Authenticate and View Dashboard
```
1. GET CSRF Token
2. POST Login (username: testuser, password: testpass123)
3. GET Dashboard → See your progress
```

### Example 2: Complete a Question
```
1. GET Select Topic
2. GET Section List (use topic_slug from response)
3. GET Section Quiz (use section_slug)
4. POST Submit Answer (with answer and question_part_id)
```

### Example 3: Take a Timed Exam
```
1. GET List Papers
2. GET Paper Detail (use slug)
3. POST Start Paper Attempt (attempt_mode: "full_timed")
4. GET Question Interface (use attempt_id from response)
5. POST Submit Answer (part_id, answer)
6. POST Complete Attempt
7. GET View Results
```

### Example 4: Ask AI Tutor
```
1. POST Info Bot (topic_slug: "complex-numbers", question: "What is...")
   → Returns AI response using RAG + GPT-4o-mini
```

## Important Notes

### Session-Based Authentication
- Django uses session cookies (not JWT tokens)
- Postman automatically stores cookies after login
- Cookies persist across requests
- Logout to clear session

### CSRF Protection
- All POST requests require CSRF token
- Run "Get CSRF Token" first
- Token auto-populated in `{{csrf_token}}` variable
- Include `X-CSRFToken` header in POST requests

### Path Variables
Replace variables in URLs:
- `:topic_slug` → e.g., "complex-numbers"
- `:section_slug` → e.g., "basic-operations"
- `:number` → Question number (1, 2, 3...)
- `:attempt_id` → From "Start Paper Attempt" response
- `:assignment_id` → From homework list

### Response Formats
- Most endpoints return HTML (for rendering in browser)
- Some endpoints return JSON (exam paper submissions, etc.)
- Check response Content-Type header

## Testing the API

### Prerequisites
1. Django development server running:
   ```bash
   python manage.py runserver
   ```

2. Valid registration code (create in admin):
   ```python
   from students.models import RegistrationCode
   code = RegistrationCode.objects.create(
       code="TESTCODE123",
       max_uses=10
   )
   ```

### Sample Test Flow
1. **Setup**: Get CSRF token
2. **Register**: Signup with registration code
3. **Login**: Authenticate
4. **Dashboard**: View initial state (0 attempts)
5. **Practice**: Submit answers to questions
6. **Dashboard**: See updated progress
7. **Exam**: Take full timed exam
8. **Results**: View exam results

## Common Issues

### "CSRF verification failed"
- Solution: Run "Get CSRF Token" request first
- Ensure `X-CSRFToken` header is included in POST requests

### "Authentication credentials required"
- Solution: Run "Login" request
- Check that cookies are enabled in Postman settings

### "Registration code invalid"
- Solution: Create valid code in Django admin
- Check code hasn't exceeded max_uses

### 404 Not Found
- Check URL path variables are correct
- Ensure topic/section slugs match database records
- Verify server is running on correct port

## API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/students/signup/` | Register new user |
| POST | `/students/login/` | Authenticate |
| GET | `/students/dashboard/` | View progress |
| GET | `/interactive/` | List topics |
| GET | `/interactive/:slug/sections/` | Topic sections |
| POST | `/interactive/:slug/sections/:section/question/:n/` | Submit answer |
| POST | `/interactive/info-bot/:slug/` | AI help |
| GET | `/exam-papers/` | List exam papers |
| POST | `/exam-papers/:slug/start/` | Start exam |
| POST | `/exam-papers/attempt/:id/submit/` | Submit exam answer |
| GET | `/notes/` | View notes |
| POST | `/notes/save-info/` | Search notes (RAG) |
| GET | `/homework/` | Student homework |

## Advanced Features

### Grading System
The API uses a sophisticated grading pipeline:
1. **Numeric normalization** - Handles fractions, decimals, angles
2. **Algebraic comparison** - Symbolic math checking
3. **GPT fallback** - AI grading for complex answers
4. **Penalty system** - Hints (-20%), Solutions (-50%)

### RAG (Retrieval-Augmented Generation)
Notes system uses:
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector search**: FAISS similarity search
- **Threshold**: 0.7 confidence (configurable)
- **Fallback**: GPT-4o-mini with top 3 notes as context

### Multi-part Questions
Questions support parts (a), (b), (c):
- Each part has own prompt, answer, max_marks
- Attempts tracked per question part
- Separate hints/solutions per part

## Environment Variables for Production

Update collection variables:
```json
{
  "base_url": "https://your-production-domain.com"
}
```

Ensure production settings:
- CSRF protection enabled
- HTTPS enforced
- Session cookies secure
- CORS configured if needed

## Support

For issues with:
- **API endpoints**: Check Django server logs
- **Authentication**: Verify CSRF token and session cookies
- **Grading**: Check `interactive_lessons/stats_tutor.py`
- **RAG/AI**: Verify OpenAI API keys in `.env`

---

**Happy Testing! 🚀**
