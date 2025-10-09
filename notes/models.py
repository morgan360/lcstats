# notes/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings
from openai import OpenAI
import hashlib
from interactive_lessons.models import Topic  # ✅ import Topic model

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class Note(models.Model):
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

    def save(self, *args, **kwargs):
        """Re-embed whenever title, topic, or metadata changes."""
        text_source = self.metadata or self.content or ""
        if text_source.strip():
            topic_name = self.topic.name if self.topic else ""
            text_to_embed = f"Title: {self.title}\nTopic: {topic_name}\n{text_source.strip()}"
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
