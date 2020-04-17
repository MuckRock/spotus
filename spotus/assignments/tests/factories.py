"""
Testing factories for the assignment app
"""

# Django
from django.utils.text import slugify

# Third Party
import factory

# SpotUs
from spotus.assignments.models import Assignment, Choice, Data, Field, Response, Value


class AssignmentFactory(factory.django.DjangoModelFactory):
    """A factory for creating Assignments"""

    class Meta:
        model = Assignment

    title = factory.Sequence("Assignment #{}".format)
    slug = factory.LazyAttribute(lambda obj: slugify(obj.title))
    user = factory.SubFactory("spotus.users.tests.factories.UserFactory")
    description = factory.Faker("sentence")


class DataFactory(factory.django.DjangoModelFactory):
    """A factory for creating Assignment Data"""

    class Meta:
        model = Data

    assignment = factory.SubFactory(AssignmentFactory)
    url = factory.Faker("url")


class FieldFactory(factory.django.DjangoModelFactory):
    """A factory for creating Assignment Fields"""

    class Meta:
        model = Field

    assignment = factory.SubFactory(AssignmentFactory)
    label = factory.Sequence("Field #{}".format)


class AssignmentTextFieldFactory(FieldFactory):
    """A factory for creating a text field"""

    type = "text"


class ChoiceFieldFactory(FieldFactory):
    """An abstract base class factory for fields with choices"""

    choice0 = factory.RelatedFactory(
        "spotus.assignments.tests.factories.ChoiceFactory", "field", order=1
    )
    choice1 = factory.RelatedFactory(
        "spotus.assignments.tests.factories.ChoiceFactory", "field", order=2
    )
    choice2 = factory.RelatedFactory(
        "spotus.assignments.tests.factories.ChoiceFactory", "field", order=3
    )


class AssignmentSelectFieldFactory(ChoiceFieldFactory):
    """A factory for creating a select field"""

    type = "select"


class AssignmentHeaderFieldFactory(ChoiceFieldFactory):
    """A factory for creating a header field"""

    type = "header"


class AssignmentCheckboxGroupFieldFactory(ChoiceFieldFactory):
    """A factory for creating a checkbox group field"""

    type = "checkbox-group"


class ChoiceFactory(factory.django.DjangoModelFactory):
    """A factory for creating a assignment choice"""

    class Meta:
        model = Choice

    field = factory.SubFactory(AssignmentSelectFieldFactory)
    choice = factory.Sequence("Choice #{}".format)
    value = factory.Sequence("choice-{}".format)


class ResponseFactory(factory.django.DjangoModelFactory):
    """A factory for creating assignment responses"""

    class Meta:
        model = Response

    assignment = factory.SubFactory(AssignmentFactory)
    user = factory.SubFactory("spotus.users.tests.factories.UserFactory")
    data = factory.SubFactory(DataFactory)


class ValueFactory(factory.django.DjangoModelFactory):
    """A factory for creating assignment values"""

    class Meta:
        model = Value

    response = factory.SubFactory(ResponseFactory)
    field = factory.SubFactory(FieldFactory)
    value = factory.Faker("word")
