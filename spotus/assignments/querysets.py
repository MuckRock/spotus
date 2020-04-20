"""Querysets for the Assignments application"""

# Django
from django.db import models
from django.db.models import Case, Count, Q, Sum, Value, When

# SpotUs
from spotus.assignments.choices import Status


class AssignmentQuerySet(models.QuerySet):
    """Object manager for assignments"""

    def get_viewable(self, user):
        """Get the viewable assignments for the user"""
        if user.is_staff:
            return self
        elif user.is_authenticated:
            return self.filter(Q(user=user) | Q(status=Status.open))
        else:
            return self.filter(status=Status.open)


class DataQuerySet(models.QuerySet):
    """Object manager for assignment data"""

    def get_choices(self, data_limit, user, ip_address):
        """Get choices for data to show"""
        choices = self.annotate(
            count=Sum(
                Case(
                    When(responses__number=1, then=Value(1)),
                    default=0,
                    output_field=models.IntegerField(),
                )
            )
        ).filter(count__lt=data_limit)
        if user is not None:
            choices = choices.exclude(responses__user=user)
        elif ip_address is not None:
            choices = choices.exclude(responses__ip_address=ip_address)
        return choices


class ResponseQuerySet(models.QuerySet):
    """Object manager for assignment responses"""

    def get_user_count(self):
        """Get the number of distinct users who have responded"""
        return self.aggregate(Count("user", distinct=True))["user__count"]

    def get_viewable(self, user):
        if user.is_staff:
            return self
        elif user.is_authenticated:
            return self.filter(Q(assignment__user=user) | Q(gallery=True)).distinct()
        else:
            return self.filter(gallery=True)
