"""
Application configuration for the assignments app
"""

# Django
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssignmentsConfig(AppConfig):
    """Assignments config"""

    name = "spotus.assignments"
    verbose_name = _("Assignments")
