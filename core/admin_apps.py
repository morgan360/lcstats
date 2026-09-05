"""
App config that swaps in the grouped admin index.

Kept out of core/apps.py: a module holding more than one AppConfig subclass
(the imported AdminConfig included) makes Django's default-config detection
ambiguous for the 'core' app itself.
"""

from django.contrib.admin.apps import AdminConfig


class NumScoilAdminConfig(AdminConfig):
    """Referenced from INSTALLED_APPS in place of 'django.contrib.admin'."""

    default_site = "core.admin_site.NumScoilAdminSite"
