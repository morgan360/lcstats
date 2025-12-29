# NumSkull Context-Aware Vision Enhancement

## Overview
NumSkull has been enhanced to be fully context-aware for exam questions, including the ability to "see" diagrams and images from exam papers using GPT-4o-mini's vision capabilities.

## What's New

### 1. Enhanced Exam Question Context
When students ask NumSkull questions while working on exam papers, NumSkull now receives:

**Text Context:**
- Exam paper year and type (e.g., "2024 Paper 1")
- Question number
- Question title (if available)
- Topic classification
- Which part they're working on (a, b, c, etc.)

**Visual Context:**
- Question diagrams/images from `ExamQuestion.image`
- Part-specific diagrams from `ExamQuestionPart.image`
- Practice question images from `Question.get_image()` and `QuestionPart.image`

### 2. Vision-Powered Responses
NumSkull can now:
- **See diagrams** in exam questions and answer questions about them
- **Analyze geometry problems** with visual diagrams
- **Interpret graphs, charts, and mathematical figures**
- **Reference specific elements** in the images when explaining concepts

### 3. How It Works

**Example Interaction:**
```
Student working on: 2024 Paper 1, Question 5(a)
Question includes a triangle diagram with sides labeled

Student asks: "How do I find the missing angle?"

NumSkull receives:
- Text: "Exam Paper: 2024 Paper 1, Question 5, Part (a), Topic: Trigonometry"
- Image: [Triangle diagram with high-resolution detail]

NumSkull responds with context-aware answer referencing the specific diagram
```

## Technical Implementation

### Backend Changes (`interactive_lessons/views.py`)

1. **Image URL Collection:**
   ```python
   question_image_urls = []  # Collect image URLs for vision
   ```

2. **Exam Question Image Extraction:**
   - Extracts `ExamQuestion.image` if available
   - Extracts `ExamQuestionPart.image` for specific parts
   - Builds absolute URLs using `request.build_absolute_uri()`

3. **Practice Question Image Extraction:**
   - Extracts images from `Question.get_image()`
   - Extracts `QuestionPart.image` for specific parts

4. **Multimodal GPT Call:**
   ```python
   if question_image_urls:
       message_content = [
           {"type": "text", "text": prompt},
           {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}}
       ]
   ```

### Vision API Configuration
- **Model:** GPT-4o-mini (supports vision)
- **Detail Level:** "high" for better diagram understanding
- **Image Format:** Supports all standard formats (PNG, JPG, etc.)

## Files Modified

### 1. `/Users/morgan/lcstats/interactive_lessons/views.py`
- Added `question_image_urls` list to collect image URLs
- Enhanced exam question context extraction with image URLs
- Enhanced practice question context extraction with image URLs
- Modified GPT API call to support multimodal messages with vision

## Benefits

### For Students:
- **Better help with diagram-based questions** - NumSkull can reference specific parts of diagrams
- **Visual problem solving** - Get help understanding geometric constructions, graphs, etc.
- **Contextual accuracy** - Answers are specific to the actual exam question they're working on

### For Exam Questions:
- **Full context awareness** - Knows which paper, year, question, and part
- **PDF-sourced diagrams** - Can see the actual diagrams from exam papers
- **Part-specific images** - Different diagrams for different parts of multi-part questions

## Testing

To test the vision feature:

1. Navigate to an exam question with an image/diagram
2. Ask NumSkull a question about the diagram, e.g.:
   - "What does the diagram show?"
   - "How are the angles labeled in this triangle?"
   - "What is the orientation of this graph?"

NumSkull should reference the specific visual elements in its response.

## Future Enhancements

Potential additions:
- **PDF text extraction** - Extract text from `ExamPaper.source_pdf`
- **Marking scheme context** - Include relevant parts of marking schemes
- **Multi-page PDF handling** - For complex multi-page questions
- **Image caching** - Cache vision API calls for repeated questions

## Notes

- Vision API calls may take slightly longer than text-only queries
- High detail mode provides best results for mathematical diagrams
- Images are sent with full resolution for maximum clarity
- The vision feature automatically activates when images are available
