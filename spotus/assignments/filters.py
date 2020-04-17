"""
Filters for Assignment models
"""

# Django
from django import forms

# Third Party
import django_filters

# SpotUs
from spotus.assignments.choices import Status
from spotus.assignments.models import Assignment
from spotus.users.models import User

NULL_BOOLEAN_CHOICES = [(None, "----------"), (True, "Yes"), (False, "No")]


class AssignmentFilterSet(django_filters.FilterSet):
    """Filtering for assignments for admins"""

    status = django_filters.ChoiceFilter(choices=Status.choices)
    is_staff = django_filters.BooleanFilter(
        field_name="user__is_staff",
        label="Staff Owned",
        widget=forms.Select(choices=NULL_BOOLEAN_CHOICES),
    )
    # XXX make this an autocomplete
    user = django_filters.ModelChoiceFilter(queryset=User.objects.all())

    class Meta:
        model = Assignment
        fields = ["status", "user"]
