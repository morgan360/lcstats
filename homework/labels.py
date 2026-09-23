"""How a piece of content is named in the homework pickers.

One definition, because the same option is built twice: by the form when the
page is rendered, and by the topic-filter endpoint when the teacher picks a
topic without saving. When those two drifted apart, the dropdown quietly
changed wording -- and, worse, changed which questions it offered.
"""


def exam_question_label(question):
    """The paper a teacher would name, including which sitting it was.

    "2022 Paper 1 (Deferred) Q8" and "2022 Paper 1 Q8" are different questions,
    and both exist.
    """
    paper = question.exam_paper
    subject = paper.subject.name if paper and paper.subject else "No subject"
    topic = question.topic.name if question.topic else "no topic"
    return f"[{subject}] {paper} Q{question.question_number} - {topic}"


def exam_part_label(part):
    """A part as the paper, question and label a teacher would say aloud."""
    paper = part.question.exam_paper
    marks = f"{part.max_marks} marks" if part.max_marks else "marks not set"
    return (f"{paper} Q{part.question.question_number}{part.label} - {marks}")
