"""Tests for assignment views"""

# pylint: disable=invalid-name

# Django
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.urls import reverse

# Standard Library
from unittest.mock import MagicMock

# Third Party
import pytest

# SpotUs
from spotus.assignments.choices import Status
from spotus.assignments.tests.factories import AssignmentFactory, ResponseFactory
from spotus.assignments.views import AssignmentDetailView, AssignmentFormView
from spotus.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def mock_middleware(request):
    """Mocks the request with messages and session middleware"""
    setattr(request, "session", MagicMock())
    setattr(request, "_messages", MagicMock())
    setattr(request, "_dont_enforce_csrf_checks", True)
    return request


class TestAssignmentDetailView:
    """Test who is allowed to see the assignment details"""

    def test_anonymous_cannot_view(self, rf):
        """Anonymous users cannot view a assignment's details"""
        assignment = AssignmentFactory()
        url = reverse(
            "assignments:detail", kwargs={"slug": assignment.slug, "pk": assignment.pk}
        )
        request = rf.get(url)
        request = mock_middleware(request)
        request.user = AnonymousUser()
        response = AssignmentDetailView.as_view()(
            request, slug=assignment.slug, pk=assignment.pk
        )
        assert response.status_code == 302

    def test_authenticated_cannot_view(self, rf):
        """Authenticated users cannot view a assignment's details"""
        assignment = AssignmentFactory()
        url = reverse(
            "assignments:detail", kwargs={"slug": assignment.slug, "pk": assignment.pk}
        )
        request = rf.get(url)
        request = mock_middleware(request)
        request.user = UserFactory()
        response = AssignmentDetailView.as_view()(
            request, slug=assignment.slug, pk=assignment.pk
        )
        assert response.status_code == 302

    def test_owner_can_view(self, rf):
        """Owner can view a assignment's details"""
        assignment = AssignmentFactory()
        url = reverse(
            "assignments:detail", kwargs={"slug": assignment.slug, "pk": assignment.pk}
        )
        request = rf.get(url)
        request = mock_middleware(request)
        request.user = assignment.user
        response = AssignmentDetailView.as_view()(
            request, slug=assignment.slug, pk=assignment.pk
        )
        assert response.status_code == 200

    def test_staff_can_view(self, rf):
        """Staff can view a assignment's details"""
        assignment = AssignmentFactory()
        url = reverse(
            "assignments:detail", kwargs={"slug": assignment.slug, "pk": assignment.pk}
        )
        request = rf.get(url)
        request = mock_middleware(request)
        request.user = UserFactory(is_staff=True)
        response = AssignmentDetailView.as_view()(
            request, slug=assignment.slug, pk=assignment.pk
        )
        assert response.status_code == 200


class TestAssignmentFormView:
    """Test who is allowed to fill out assignment forms"""

    def test_public(self, rf):
        """Anybody can fill out a public assignment"""
        assignment = AssignmentFactory(status=Status.open)
        url = reverse(
            "assignments:assignment",
            kwargs={"slug": assignment.slug, "pk": assignment.pk},
        )
        request = rf.get(url)
        request = mock_middleware(request)
        request.user = AnonymousUser()
        response = AssignmentFormView.as_view()(
            request, slug=assignment.slug, pk=assignment.pk
        )
        assert response.status_code == 200

    def test_has_assignment_limit(self, rf):
        """Test the has assignment method with a user limit"""
        # pylint: disable=protected-access
        view = AssignmentFormView()
        assignment = AssignmentFactory(user_limit=True)
        user = UserFactory()
        ip_address = "127.0.0.1"

        # the user hasn't replied yet, should have an assignment
        assert view._has_assignment(assignment, user, None)

        # the user replied, they may not reply again
        ResponseFactory(assignment=assignment, user=user)
        assert not (view._has_assignment(assignment, user, None))

        # the ip address hasn't replied yet, should have an assignment
        assert view._has_assignment(assignment, AnonymousUser(), ip_address)

        # the ip address replied, they may not reply again
        ResponseFactory(assignment=assignment, user=None, ip_address=ip_address)
        assert not view._has_assignment(assignment, AnonymousUser(), ip_address)

    def test_has_assignment_no_limit(self, rf):
        """Test the has assignment method without a user limit"""
        # pylint: disable=protected-access
        view = AssignmentFormView()
        assignment = AssignmentFactory(user_limit=False)
        user = UserFactory()
        ip_address = "127.0.0.1"

        # should always return true

        # the user hasn't replied yet, should have an assignment
        assert view._has_assignment(assignment, user, None)

        # the user replied, they may reply again
        ResponseFactory(assignment=assignment, user=user)
        assert view._has_assignment(assignment, user, None)

        # the ip address hasn't replied yet, should have an assignment
        assert view._has_assignment(assignment, AnonymousUser(), ip_address)

        # the ip address replied, they may reply again
        ResponseFactory(assignment=assignment, user=None, ip_address=ip_address)
        assert view._has_assignment(assignment, AnonymousUser(), ip_address)
