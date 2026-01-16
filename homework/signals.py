from django.db.models.signals import post_save
from django.contrib.auth.models import Group
from django.dispatch import receiver
from .models import TeacherProfile


@receiver(post_save, sender=TeacherProfile)
def add_teacher_to_group(sender, instance, created, **kwargs):
    """
    When a TeacherProfile is created, add the user to the Teachers group.
    This allows teachers to access teacher-specific views without is_staff=True.
    """
    if created:
        teachers_group, _ = Group.objects.get_or_create(name='Teachers')
        instance.user.groups.add(teachers_group)