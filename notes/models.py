# notes/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings
from openai import OpenAI
import hashlib
from interactive_lessons.models import Topic  # ✅ import Topic model

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class Note(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('general', 'General Note'),
        ('exam_paper', 'Exam Paper'),
        ('marking_scheme', 'Marking Scheme'),
    ]

    PAPER_TYPE_CHOICES = [
        ('p1', 'Paper 1'),
        ('p2', 'Paper 2'),
    ]

    title = models.CharField(max_length=200)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notes",
        help_text="Select topic from interactive lessons"
    )
    content = models.TextField()
    metadata = models.TextField(blank=True, null=True, help_text="Sample prompts or summary for embedding")
    image = models.ImageField(upload_to="notes/", blank=True, null=True)
    embedding = models.JSONField(null=True, blank=True)
    _content_hash = models.CharField(max_length=64, blank=True, null=True, editable=False)

    # Exam paper specific fields
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        default='general',
        help_text="Type of content (general note, exam paper, or marking scheme)"
    )
    exam_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Year of the exam (e.g., 2024)"
    )
    paper_type = models.CharField(
        max_length=10,
        choices=PAPER_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Paper 1 or Paper 2"
    )
    question_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Specific question number or range (e.g., 'Q1', 'Q3(a)', '1-3')"
    )
    gdrive_file_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Google Drive file ID for source document"
    )
    gdrive_link = models.URLField(
        blank=True,
        null=True,
        help_text="Public link to Google Drive file"
    )

    def _clean_content_for_embedding(self, content):
        """Clean content by removing markdown formatting and artifacts for better embeddings."""
        import re

        # Remove common prefixes
        content = re.sub(r'^(ChatGPT said:|AI said:|Assistant:)\s*\n?', '', content, flags=re.MULTILINE)

        # Remove LaTeX delimiters but keep the content
        content = re.sub(r'\$\$([^\$]+)\$\$', r'\1', content)  # Display math
        content = re.sub(r'\$([^\$]+)\$', r'\1', content)      # Inline math

        # Remove markdown bold/italic but keep text
        content = re.sub(r'\*\*([^\*]+)\*\*', r'\1', content)  # Bold
        content = re.sub(r'\*([^\*]+)\*', r'\1', content)      # Italic
        content = re.sub(r'__([^_]+)__', r'\1', content)       # Bold alt
        content = re.sub(r'_([^_]+)_', r'\1', content)         # Italic alt

        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n', '\n', content)  # Multiple newlines
        content = re.sub(r' +', ' ', content)         # Multiple spaces

        return content.strip()

    def save(self, *args, **kwargs):
        """Re-embed whenever title, topic, or metadata changes."""
        # Strategy: Combine title, topic, metadata AND cleaned content for richer embeddings
        topic_name = self.topic.name if self.topic else ""

        # Build comprehensive text for embedding
        parts = [f"Topic: {topic_name}", f"Title: {self.title}"]

        # Add metadata if available (contains key questions/terms)
        if self.metadata and self.metadata.strip():
            parts.append(f"Key concepts: {self.metadata.strip()}")

        # Always include cleaned content for semantic richness
        cleaned_content = self._clean_content_for_embedding(self.content or "")
        if cleaned_content:
            parts.append(f"Content: {cleaned_content}")

        text_to_embed = "\n".join(parts)

        if text_to_embed.strip():
            content_hash = hashlib.md5(text_to_embed.encode()).hexdigest()

            # Only regenerate embedding if text changed
            if content_hash != self._content_hash:
                print(f"🔄 Re-embedding note: {self.title}")
                response = client.embeddings.create(
                    model=settings.OPENAI_EMBED_MODEL,
                    input=text_to_embed,
                )
                self.embedding = response.data[0].embedding
                self._content_hash = content_hash

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def topic_name(self):
        """Convenience property for templates or logs."""
        return self.topic.name if self.topic else "No topic"


class InfoBotQuery(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    topic_slug = models.SlugField(blank=True, null=True)
    question = models.TextField()
    answer = models.TextField(blank=True)
    confidence = models.FloatField(null=True, blank=True)
    sources = models.TextField(blank=True, help_text="Comma-separated list of retrieved note titles")
    source_type = models.CharField(
        max_length=20,
        choices=[("notes", "Notes"), ("ai", "AI Generated"), ("mixed", "Mixed")],
        default="ai",
    )

    def __str__(self):
        return f"{self.topic_slug}: {self.question[:60]}"
