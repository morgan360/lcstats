from django.db.models.signals import post_save
from django.contrib.auth.models import Group
from django.dispatch import receiver
from .models import TeacherProfile


@receiver(post_save, sender=TeacherProfile)
def add_teacher_to_group(sender, instance, created, **kwargs):
    """
    When a TeacherProfile is created, add the user to the Teachers group
    and Teacher Admins group (for homework management in Django Admin).
    """
    if created:
        # Add to Teachers group (for Teacher Dashboard access)
        teachers_group, _ = Group.objects.get_or_create(name='Teachers')
        instance.user.groups.add(teachers_group)

        # Add to Teacher Admins group (for Django Admin homework access)
        teacher_admins_group, _ = Group.objects.get_or_create(name='Teacher Admins')
        instance.user.groups.add(teacher_admins_group)

        # Give is_staff so they can access Django Admin
        instance.user.is_staff = True
        instance.user.save()