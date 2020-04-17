# Django
from django.utils.translation import gettext_lazy as _

# Third Party
from djchoices import ChoiceItem, DjangoChoices


class Status(DjangoChoices):
    draft = ChoiceItem(0, _("Draft"))
    open = ChoiceItem(1, _("Open"))
    closed = ChoiceItem(2, _("Closed"))


class Registration(DjangoChoices):
    required = ChoiceItem(0, _("Required"))
    off = ChoiceItem(1, _("Off"))
    optional = ChoiceItem(2, _("Optional"))
