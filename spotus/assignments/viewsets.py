"""
Viewsets for the Assignment application API
"""

# Django
from django.db.models import Q
from rest_framework import mixins, permissions, viewsets

# Third Party
from django_filters import rest_framework as django_filters

# SpotUs
from spotus.assignments.models import Assignment, Response
from spotus.assignments.serializers import (
    ResponseAdminSerializer,
    ResponseGallerySerializer,
)


class DjangoObjectPermissionsOrAnonReadOnly(permissions.DjangoObjectPermissions):
    """Use Django Object permissions as the base for our permissions
    Allow anonymous read-only access
    """

    authenticated_users_only = False


class ResponseViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """API views for Response"""

    queryset = (
        Response.objects.select_related("assignment", "data", "user", "edit_user")
        .prefetch_related("assignment__fields", "values", "tags")
        .order_by("id")
    )
    permission_classes = (DjangoObjectPermissionsOrAnonReadOnly,)

    def get_serializer_class(self):
        """Get the serializer class"""
        if self.request.user.is_staff:
            return ResponseAdminSerializer
        try:
            assignment = Assignment.objects.get(pk=self.request.GET.get("assignment"))
        except Assignment.DoesNotExist:
            return ResponseGallerySerializer

        if self.request.user.has_perm("assignment.change_assignment", assignment):
            return ResponseAdminSerializer
        else:
            return ResponseGallerySerializer

    def get_queryset(self):
        """Filter the queryset"""
        # XXX this should be a queryset method
        if self.request.user.is_staff:
            return self.queryset
        elif self.request.user.is_authenticated:
            return self.queryset.filter(
                Q(assignment__user=self.request.user) | Q(gallery=True)
            ).distinct()
        else:
            return self.queryset.filter(gallery=True)

    class Filter(django_filters.FilterSet):
        """API Filter for Assignment Responses"""

        assignment = django_filters.NumberFilter(name="assignment__id")

        class Meta:
            model = Response
            fields = ("id", "flag")

    filter_class = Filter
    search_fields = ("values__value", "tags__name")
