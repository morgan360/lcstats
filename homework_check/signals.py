from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import CheckPhoto, InboundScan


@receiver(post_delete, sender=CheckPhoto)
def delete_check_photo_file(sender, instance, **kwargs):
    """Remove the photo from disk when its row goes.

    Django deletes the row and leaves the file, which for a photograph of a
    named child's work would mean "deleted" did not actually delete anything.
    save=False because the row is already gone.
    """
    if instance.image:
        instance.image.delete(save=False)


@receiver(post_delete, sender=InboundScan)
def delete_inbound_scan_files(sender, instance, **kwargs):
    """The same guarantee for an emailed scan and its first-page thumbnail."""
    if instance.pdf:
        instance.pdf.delete(save=False)
    if instance.thumbnail:
        instance.thumbnail.delete(save=False)
