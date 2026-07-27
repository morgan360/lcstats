from django.db import migrations

PRESETS = [
    # (category, tone, text, order)
    ('behaviour', 'positive', 'Excellent focus and effort today', 1),
    ('behaviour', 'positive', 'Helped another student — great to see', 2),
    ('behaviour', 'positive', 'Asked thoughtful questions', 3),
    ('behaviour', 'neutral', 'Quiet today, seemed tired', 10),
    ('behaviour', 'neutral', 'Needed a reminder to start work', 11),
    ('behaviour', 'concern', 'Chatty — needed redirection more than once', 20),
    ('behaviour', 'concern', 'Disruptive in class', 21),
    ('behaviour', 'concern', 'Phone out during class', 22),
    ('test', 'positive', 'Excellent work — well prepared', 1),
    ('test', 'positive', 'Big improvement on last test', 2),
    ('test', 'neutral', 'Careless slips — knows the material', 10),
    ('test', 'neutral', 'Ran out of time on later questions', 11),
    ('test', 'concern', 'Needs revision of this topic', 20),
    ('test', 'concern', 'Did not attempt several questions', 21),
]


def seed_presets(apps, schema_editor):
    CommentPreset = apps.get_model('reports', 'CommentPreset')
    for category, tone, text, order in PRESETS:
        CommentPreset.objects.get_or_create(
            category=category, text=text, defaults={'tone': tone, 'order': order}
        )


def unseed_presets(apps, schema_editor):
    CommentPreset = apps.get_model('reports', 'CommentPreset')
    CommentPreset.objects.filter(text__in=[p[2] for p in PRESETS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_presets, unseed_presets),
    ]
