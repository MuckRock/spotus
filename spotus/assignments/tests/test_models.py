"""Tests for assignment models"""

# Django
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

# Standard Library
import json
from datetime import datetime

# Third Party
import pytest

# SpotUs
from spotus.assignments.choices import Status
from spotus.assignments.models import Assignment
from spotus.assignments.tests.factories import (
    AssignmentCheckboxGroupFieldFactory,
    AssignmentFactory,
    AssignmentHeaderFieldFactory,
    AssignmentSelectFieldFactory,
    AssignmentTextFieldFactory,
    DataFactory,
    ResponseFactory,
    ValueFactory,
)
from spotus.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestAssignment:
    """Test the Assignment model"""

    def test_get_data_to_show(self):
        """Get data to show should pick the correct data"""
        assignment = AssignmentFactory()
        ip_address = None
        assert assignment.get_data_to_show(assignment.user, ip_address) is None
        data = DataFactory(assignment=assignment)
        assert data == assignment.get_data_to_show(assignment.user, ip_address)

    def test_create_form(self):
        """Create form should create fields from the JSON"""
        assignment = AssignmentFactory()
        AssignmentTextFieldFactory(assignment=assignment, label="Delete Me", order=0)
        assignment.create_form(
            json.dumps(
                [
                    {
                        "label": "Text Field",
                        "type": "text",
                        "description": "Here is some help",
                    },
                    {
                        "label": "Select Field",
                        "type": "select",
                        "values": [
                            {"label": "Choice 1", "value": "choice-1"},
                            {"label": "Choice 2", "value": "choice-2"},
                        ],
                    },
                ]
            )
        )
        assert assignment.fields.get(label="Delete Me").deleted
        assert assignment.fields.filter(
            label="Text Field", type="text", help_text="Here is some help", order=0
        ).exists()
        assert assignment.fields.filter(
            label="Select Field", type="select", order=1
        ).exists()
        assert assignment.fields.get(label="Select Field").choices.count() == 2

    def test_uniqify_label_name(self):
        """Uniqify label name should give each label a unqiue name"""
        # pylint: disable=protected-access
        assignment = AssignmentFactory()
        seen = set()
        assert assignment._uniqify_label_name(seen, "one") == "one"
        assert assignment._uniqify_label_name(seen, "one") == "one-1"
        assert assignment._uniqify_label_name(seen, "two") == "two"
        assert assignment._uniqify_label_name(seen, "one") == "one-2"
        assert assignment._uniqify_label_name(seen, "two") == "two-1"

    def test_get_form_json(self):
        """Get the JSON to rebuild the form builder"""
        assignment = AssignmentFactory()
        AssignmentTextFieldFactory(
            assignment=assignment, label="Text Field", help_text="Help", order=0
        )
        AssignmentSelectFieldFactory(
            assignment=assignment, label="Select Field", order=1
        )
        form_data = json.loads(assignment.get_form_json())
        assert form_data[0]["type"] == "text"
        assert form_data[0]["label"] == "Text Field"
        assert form_data[0]["description"] == "Help"

        assert form_data[1]["type"] == "select"
        assert form_data[1]["label"] == "Select Field"
        assert len(form_data[1]["values"]) == 3
        assert set(form_data[1]["values"][0].keys()) == {"value", "label"}

    def test_get_header_values(self):
        """Get the header values for CSV export"""
        assignment = AssignmentFactory()
        AssignmentTextFieldFactory(
            assignment=assignment, label="Text Field", help_text="Help", order=0
        )
        AssignmentHeaderFieldFactory(assignment=assignment, label="Header", order=1)
        AssignmentSelectFieldFactory(
            assignment=assignment, label="Select Field", order=2
        )
        assert assignment.get_header_values(["meta"]) == [
            "user",
            "public",
            "datetime",
            "skip",
            "flag",
            "gallery",
            "tags",
            "Text Field",
            "Select Field",
        ]
        assignment.multiple_per_page = True
        assert assignment.get_header_values(["meta"]) == [
            "user",
            "public",
            "datetime",
            "skip",
            "flag",
            "gallery",
            "tags",
            "number",
            "Text Field",
            "Select Field",
        ]
        DataFactory(assignment=assignment)
        assert assignment.get_header_values(["meta"]) == [
            "user",
            "public",
            "datetime",
            "skip",
            "flag",
            "gallery",
            "tags",
            "number",
            "datum",
            "meta",
            "Text Field",
            "Select Field",
        ]

    def test_get_metadata_keys(self):
        """Get the metadata keys associated with this crowdsoucre's data"""
        assignment = AssignmentFactory()
        assert assignment.get_metadata_keys() == []
        data = DataFactory(assignment=assignment)
        assert assignment.get_metadata_keys() == []
        data.metadata = {"foo": "bar", "muck": "rock"}
        data.save()
        assert set(assignment.get_metadata_keys()) == {"foo", "muck"}

    def test_get_viewable(self):
        """Get the list of viewable assignments for the user"""
        admin = UserFactory(is_staff=True)
        owner, user = UserFactory.create_batch(2)

        draft_assignment = AssignmentFactory(user=owner, status=Status.draft)
        open_assignment = AssignmentFactory(user=owner, status=Status.open)
        closed_assignment = AssignmentFactory(user=owner, status=Status.closed)

        assignments = Assignment.objects.get_viewable(admin)
        assert draft_assignment in assignments
        assert open_assignment in assignments
        assert closed_assignment in assignments

        assignments = Assignment.objects.get_viewable(owner)
        assert draft_assignment in assignments
        assert open_assignment in assignments
        assert closed_assignment in assignments

        assignments = Assignment.objects.get_viewable(user)
        assert draft_assignment not in assignments
        assert open_assignment in assignments
        assert closed_assignment not in assignments

        assignments = Assignment.objects.get_viewable(AnonymousUser())
        assert draft_assignment not in assignments
        assert open_assignment in assignments
        assert closed_assignment not in assignments


class TestData:
    """Test the Assignment Data model"""

    def test_get_choices(self):
        """Test the get choices queryset method"""
        assignment = AssignmentFactory()
        data = DataFactory.create_batch(4, assignment=assignment)
        user = assignment.user
        ip_address = "127.0.0.1"
        limit = 2

        # all data should be valid choices
        assert set(assignment.data.get_choices(limit, user, None)) == set(data)
        # if I respond to one, it is no longer a choice for me
        ResponseFactory(assignment=assignment, user=assignment.user, data=data[0])
        assert set(assignment.data.get_choices(limit, user, None)) == set(data[1:])
        # if one has at least `limit` responses, it is no longer a valid choice
        ResponseFactory.create_batch(2, assignment=assignment, data=data[1])
        assert set(assignment.data.get_choices(limit, user, None)) == set(data[2:])
        # multiple responses from the same user only count once
        new_user = UserFactory()
        ResponseFactory(assignment=assignment, user=new_user, data=data[2], number=1)
        ResponseFactory(assignment=assignment, user=new_user, data=data[2], number=2)
        assert set(assignment.data.get_choices(limit, user, None)) == set(data[2:])
        # if I anonymously to one, it is no longer a choice for me
        ResponseFactory(assignment=assignment, ip_address=ip_address, data=data[3])
        assert set(assignment.data.get_choices(limit, None, ip_address)) == set(
            [data[0], data[2]]
        )


class TestResponse:
    """Test the Assignment Response model"""

    def test_get_values(self):
        """Test getting the values from the response"""
        assignment = AssignmentFactory()
        response = ResponseFactory(
            assignment=assignment,
            user__username="Username",
            datetime=datetime(2017, 1, 2, tzinfo=timezone.get_current_timezone()),
            data=None,
        )
        field = AssignmentTextFieldFactory(assignment=assignment, order=0)
        AssignmentHeaderFieldFactory(assignment=assignment, order=1)
        ValueFactory(response=response, field=field, value="Value")

        assert response.get_values([]) == [
            "Username",
            False,
            "2017-01-02 00:00:00",
            False,
            False,
            False,
            "",
            "Value",
        ]

    def test_get_values_blank(self):
        """Test getting the values from the response
        Blank responses should only be ignored for multiselect fields
        """
        assignment = AssignmentFactory()
        response = ResponseFactory(
            assignment=assignment,
            user__username="Username",
            public=True,
            datetime=datetime(2017, 1, 2, tzinfo=timezone.get_current_timezone()),
            data=None,
        )
        text_field = AssignmentTextFieldFactory(assignment=assignment, order=0)
        ValueFactory(response=response, field=text_field, value="")
        check_field = AssignmentCheckboxGroupFieldFactory(
            assignment=assignment, order=1
        )
        ValueFactory(response=response, field=check_field, value="")
        ValueFactory(response=response, field=check_field, value="Foo")
        ValueFactory(response=response, field=check_field, value="Foo")
        check_field2 = AssignmentCheckboxGroupFieldFactory(
            assignment=assignment, order=2
        )
        ValueFactory(response=response, field=check_field2, value="")

        assert response.get_values([]) == [
            "Username",
            True,
            "2017-01-02 00:00:00",
            False,
            False,
            False,
            "",
            "",
            "Foo, Foo",
            "",
        ]
