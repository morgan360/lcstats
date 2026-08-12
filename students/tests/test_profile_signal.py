"""Saving a user who has no StudentProfile must not explode.

This was a live 500 on production: allauth wipes the password when it connects
a Google account to an existing user, that wipe calls
User.save(update_fields=["password"]), and the post_save signal reached through
instance.studentprofile - which raises RelatedObjectDoesNotExist for any account
without one. Two of 28 production users were in that state, so the Google
callback died after the password had already been cleared, locking the account
out of both login methods.
"""
from django.contrib.auth.models import User
from django.test import TestCase

from students.models import StudentProfile


class UserSaveWithoutProfileTests(TestCase):
    def test_saving_a_user_missing_its_profile_recreates_it(self):
        user = User.objects.create_user("orphan", password="x")
        StudentProfile.objects.filter(user=user).delete()
        self.assertFalse(StudentProfile.objects.filter(user=user).exists())

        # Refetch: the signal populates the reverse one-to-one cache when it
        # creates the profile, so the original instance would hand back a stale
        # cached object and never reproduce the bug.
        user = User.objects.get(pk=user.pk)
        user.first_name = "Recovered"
        user.save()  # used to raise RelatedObjectDoesNotExist

        self.assertTrue(StudentProfile.objects.filter(user=user).exists())

    def test_password_wipe_on_a_profileless_user_succeeds(self):
        """The exact production path: allauth's wipe calls save(update_fields)."""
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.internal.flows.email_authentication import (
            wipe_password,
        )

        user = User.objects.create_user(
            "orphan2", email="orphan2@example.com", password="original"
        )
        StudentProfile.objects.filter(user=user).delete()
        EmailAddress.objects.create(
            user=user, email="orphan2@example.com", verified=False, primary=True
        )

        user = User.objects.get(pk=user.pk)  # drop the cached reverse relation
        wipe_password(None, user, "orphan2@example.com")

        user.refresh_from_db()
        self.assertFalse(user.has_usable_password())
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())

    def test_existing_profile_is_still_saved_not_duplicated(self):
        user = User.objects.create_user("normal", password="x")
        self.assertEqual(StudentProfile.objects.filter(user=user).count(), 1)

        user = User.objects.get(pk=user.pk)
        user.save()

        self.assertEqual(StudentProfile.objects.filter(user=user).count(), 1)
