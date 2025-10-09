
from django.shortcuts import render
from openai import OpenAI
from notes.utils import search_similar
import markdown
from django.utils.safestring import mark_safe


client = OpenAI()

import re
import markdown
from django.shortcuts import render
from django.utils.safestring import mark_safe
from openai import OpenAI
from notes.utils import search_similar


client = OpenAI()

def chat_view(request):
    query = request.GET.get("query")
    answer = None
    retrieved_notes = []

    if query:
        # Step 1: Get related notes for context
        retrieved = search_similar(query)
        retrieved_notes = [note.content for _, note in retrieved]
        context_text = "\n\n".join(retrieved_notes)

        # Step 2: Build the tutoring prompt
        prompt = f"""
        You are a Leaving Cert Honours Maths tutor.
        Explain or solve the following question clearly and step-by-step.
        Use LaTeX for any maths formulas (use $...$ for inline and $$...$$ for display).

        Question:
        {query}

        Helpful background notes:
        {context_text}
        """

        # Step 3: Get GPT answer
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw_answer = response.choices[0].message.content.strip()

        # Step 4: Convert Markdown → HTML
        answer_html = markdown.markdown(
            raw_answer,
            extensions=["fenced_code", "tables"],
            output_format="html5",
        )

        # Step 5: Fix escaped backslashes for MathJax
        answer_html = re.sub(r"\\\\", r"\\", answer_html)

        answer = mark_safe(answer_html)

    context = {
        "query": query,
        "answer": answer,
        "notes": retrieved_notes,
    }
    return render(request, "chat/chat.html", context)

