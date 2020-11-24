"""Models for the Crowdsource application"""

# Django
from django.conf import settings
from django.contrib.postgres.aggregates import StringAgg
from django.contrib.postgres.fields import JSONField
from django.core.mail.message import EmailMessage
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models.aggregates import Count
from django.db.models.expressions import Case, Value as V, When
from django.db.models.functions import Concat, TruncDay
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

# Standard Library
import json
from html import unescape
from random import choice

# Third Party
from bleach.sanitizer import Cleaner
from pkg_resources import resource_filename
from pyembed.core import PyEmbed
from pyembed.core.consumer import PyEmbedConsumerError
from pyembed.core.discovery import AutoDiscoverer, ChainingDiscoverer, FileDiscoverer
from taggit.managers import TaggableManager

# SpotUs
from spotus.assignments import fields
from spotus.assignments.choices import Registration, Status
from spotus.assignments.constants import DOCUMENT_URL_RE
from spotus.assignments.querysets import (
    AssignmentQuerySet,
    DataQuerySet,
    ResponseQuerySet,
)


class Assignment(models.Model):
    """An Assignment"""

    title = models.CharField(_("title"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255)
    user = models.ForeignKey(
        verbose_name=_("user"),
        to="users.User",
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    datetime_created = models.DateTimeField(_("datetime created"), default=timezone.now)
    datetime_opened = models.DateTimeField(_("datetime opened"), blank=True, null=True)
    datetime_closed = models.DateTimeField(_("datetime closed"), blank=True, null=True)
    status = models.IntegerField(
        _("status"), default=Status.draft, choices=Status.choices
    )
    description = models.TextField(_("description"), help_text="May use markdown")
    data_limit = models.PositiveSmallIntegerField(
        _("data limit"),
        default=3,
        help_text=_(
            "Number of times each data assignment will be completed "
            "(by different users) - only used if using data for this assignment"
        ),
        validators=[MinValueValidator(1)],
    )
    multiple_per_page = models.BooleanField(
        _("allow multiple submissions per data item"),
        default=False,
        help_text=_(
            "This is useful for cases when there may be multiple "
            "records of interest per data source"
        ),
    )
    user_limit = models.BooleanField(
        _("user limit"),
        default=True,
        help_text=_(
            "Is the user limited to completing this form only once? "
            "(else, it is unlimited) - only used if not using data for this assignment"
        ),
    )
    registration = models.IntegerField(
        _("registration"),
        default=Registration.required,
        choices=Registration.choices,
        help_text=("Is registration required to complete this assignment?"),
    )
    submission_emails = models.TextField(_("submission emails"))
    featured = models.BooleanField(
        _("featured"),
        default=False,
        help_text="Featured assignments will appear on the homepage.",
    )
    ask_public = models.BooleanField(
        _("ask public"),
        default=True,
        help_text=_(
            "Add a field asking users if we can publically credit them "
            "for their response"
        ),
    )

    objects = AssignmentQuerySet.as_manager()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("assignments:detail", kwargs={"slug": self.slug, "pk": self.pk})

    def get_data_to_show(self, user, ip_address):
        """Get the assignment data to show"""
        options = self.data.get_choices(self.data_limit, user, ip_address)
        if options:
            return choice(options)
        else:
            return None

    @transaction.atomic
    def create_form(self, form_json):
        """Create the assignment form from the form builder json"""
        form_data = json.loads(form_json)
        seen_labels = set()
        cleaner = Cleaner(tags=[], attributes={}, styles=[], strip=True)
        # reset the order for all fields to avoid violating the unique constraint
        # it also allows for detection of deleted fields
        self.fields.update(order=None)
        for order, field_data in enumerate(form_data):
            label = cleaner.clean(field_data["label"])[:255]
            label = unescape(label)
            label = self._uniqify_label_name(seen_labels, label)
            description = cleaner.clean(field_data.get("description", ""))[:255]
            kwargs = {
                "label": label,
                "type": field_data["type"],
                "help_text": description,
                "min": field_data.get("min"),
                "max": field_data.get("max"),
                "required": field_data.get("required", False),
                "gallery": field_data.get("gallery", False),
                "order": order,
            }
            try:
                field = self.fields.get(pk=field_data.get("name"))
                self.fields.filter(pk=field.pk).update(**kwargs)
            except (Field.DoesNotExist, ValueError):
                field = self.fields.create(**kwargs)

            if "values" in field_data and field.field.accepts_choices:
                # delete existing choices and re-create them to avoid
                # violating unique constraints on edits, and to delete removed
                # choices - responses store by value, so this does not destroy
                # any data
                field.choices.all().delete()
                for choice_order, value in enumerate(field_data["values"]):
                    field.choices.update_or_create(
                        choice=cleaner.clean(value["label"])[:255],
                        defaults=dict(
                            value=cleaner.clean(value["value"])[:255],
                            order=choice_order,
                        ),
                    )
        # any field which has no order after all fields are
        # re-created has been deleted
        self.fields.filter(order=None).update(deleted=True)

    def _uniqify_label_name(self, seen_labels, label):
        """Ensure the label names are all unique"""
        new_label = label
        i = 0
        while new_label in seen_labels:
            i += 1
            postfix = str(i)
            new_label = "{}-{}".format(label[: 254 - len(postfix)], postfix)
        seen_labels.add(new_label)
        return new_label

    def get_form_json(self):
        """Get the form JSON for editing the form"""
        return json.dumps([f.get_json() for f in self.fields.filter(deleted=False)])

    def get_header_values(self, metadata_keys, include_emails=False):
        """Get header values for CSV export"""
        values = ["user", "public", "datetime", "skip", "flag", "gallery", "tags"]
        if include_emails:
            values.insert(1, "email")
        if self.multiple_per_page:
            values.append("number")
        if self.data.exists():
            values.append("datum")
            values.extend(metadata_keys)
        field_labels = list(
            self.fields.exclude(type__in=fields.STATIC_FIELDS).values_list(
                Case(
                    When(deleted=True, then=Concat("label", V(" (deleted)"))),
                    default="label",
                ),
                flat=True,
            )
        )
        return values + field_labels

    def get_metadata_keys(self):
        """Get the metadata keys for this assignment's data"""
        datum = self.data.first()
        if datum:
            return list(datum.metadata.keys())
        else:
            return []

    def total_assignments(self):
        """Total assignments to be completed"""
        if not self.data.all():
            return None
        return len(self.data.all()) * self.data_limit

    def percent_complete(self):
        """Percent of tasks complete"""
        total = self.total_assignments()
        if not total:
            return 0
        return int(100 * self.responses.count() / float(total))

    def contributor_line(self):
        """Line about who has contributed"""
        responses = self.responses.select_related("user")
        users = list({r.user for r in responses if r.user and r.public})
        total = len(users)

        def join_names(users):
            """Create a comma seperated list of user names"""
            return ", ".join(u.name or u.username for u in users)

        if total > 4:
            return "{} and {} others helped".format(join_names(users[:3]), total - 3)
        elif total > 1:
            return "{} and {} helped".format(
                join_names(users[:-1]), users[-1].name or users[-1].username
            )
        elif total == 1:
            return "{} helped".format(users[0].name or users[0].username)
        elif responses:
            # there have been responses, but none of them are public
            return ""
        else:
            return "No one has helped yet, be the first!"

    def responses_per_day(self):
        """How many responses there have been per day"""
        return (
            self.responses.annotate(date=TruncDay("datetime"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

    class Meta:
        verbose_name = _("assignment")
        permissions = (
            (
                "form_assignment",
                "Can view and fill out the assignments for this assignment",
            ),
        )


DOCCLOUD_EMBED = """
<div class="DC-embed DC-embed-document DV-container">
  <div style="position:relative;padding-bottom:129.42857142857142%;height:0;overflow:hidden;max-width:100%;">
    <iframe
        src="//www.documentcloud.org/documents/{doc_id}.html?
            embed=true&amp;responsive=false&amp;sidebar=false"
        title="{doc_id} (Hosted by DocumentCloud)"
        sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
        frameborder="0"
        style="position:absolute;top:0;left:0;width:100%;height:100%;border:1px solid #aaa;border-bottom:0;box-sizing:border-box;">
    </iframe>
  </div>
</div>
"""


class Data(models.Model):
    """A source of data to show with the assignment questions"""

    assignment = models.ForeignKey(
        verbose_name=_("assignment"),
        to=Assignment,
        on_delete=models.CASCADE,
        related_name="data",
    )
    url = models.URLField(_("URL"), max_length=255, blank=True)
    metadata = JSONField(_("metadata"), default=dict, blank=True)

    objects = DataQuerySet.as_manager()

    def __str__(self):
        return f"Crowdsource Data: {self.url}"

    def embed(self):
        """Get the html to embed into the assignment"""
        if self.url:
            try:
                # first try to get embed code from oEmbed
                return mark_safe(
                    PyEmbed(
                        # we don't use the default discoverer because it contains a bug
                        # that makes it always match spotify
                        discoverer=ChainingDiscoverer(
                            [
                                FileDiscoverer(
                                    resource_filename(__name__, "oembed_providers.json")
                                ),
                                AutoDiscoverer(),
                            ]
                        )
                    ).embed(self.url, max_height=400)
                )
            except PyEmbedConsumerError:
                # if this is a private document cloud document, it will not have
                # an oEmbed, create the embed manually
                doc_match = DOCUMENT_URL_RE.match(self.url)
                if doc_match:
                    return mark_safe(
                        DOCCLOUD_EMBED.format(doc_id=doc_match.group("doc_id"))
                    )
                else:
                    # fall back to a simple iframe
                    return format_html(
                        '<iframe src="{}" width="100%" height="400px"></iframe>',
                        self.url,
                    )

    class Meta:
        verbose_name = _("assignment data")


class Field(models.Model):
    """A field on an assignment form"""

    assignment = models.ForeignKey(
        verbose_name=_("assignment"),
        to=Assignment,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    label = models.CharField(_("label"), max_length=255)
    type = models.CharField(_("type"), max_length=15, choices=fields.FIELD_CHOICES)
    help_text = models.CharField(_("help text"), max_length=255, blank=True)
    min = models.PositiveSmallIntegerField(_("minimum"), blank=True, null=True)
    max = models.PositiveSmallIntegerField(_("maximum"), blank=True, null=True)
    required = models.BooleanField(_("required"), default=True)
    gallery = models.BooleanField(_("gallery"), default=False)
    order = models.PositiveSmallIntegerField(_("order"), blank=True, null=True)
    deleted = models.BooleanField(_("deleted"), default=False)

    def __str__(self):
        if self.deleted:
            return f"{self.label} (Deleted)"
        else:
            return self.label

    def get_form_field(self):
        """Return a form field appropriate for rendering this field"""
        return self.field().get_form_field(self)

    def get_json(self):
        """Get the JSON represenation for this field"""
        data = {
            "type": self.type,
            "label": self.label,
            "description": self.help_text,
            "required": self.required,
            "gallery": self.gallery,
            "name": str(self.pk),
        }
        if self.field.accepts_choices:
            data["values"] = [
                {"label": c.choice, "value": c.value} for c in self.choices.all()
            ]
        if self.min is not None:
            data["min"] = self.min
        if self.max is not None:
            data["max"] = self.max
        return data

    @property
    def field(self):
        """Get the assignment field instance"""
        return fields.FIELD_DICT[self.type]

    class Meta:
        verbose_name = _("assignment field")
        ordering = ("order",)
        unique_together = (("assignment", "label"), ("assignment", "order"))


class Choice(models.Model):
    """A choice presented to assignment users"""

    field = models.ForeignKey(
        verbose_name=_("field"),
        to=Field,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    choice = models.CharField(_("choice"), max_length=255)
    value = models.CharField(_("value"), max_length=255)
    order = models.PositiveSmallIntegerField(_("order"))

    def __str__(self):
        return self.choice

    class Meta:
        verbose_name = _("assignment choice")
        ordering = ("order",)
        unique_together = (("field", "choice"), ("field", "order"))


class Response(models.Model):
    """A response to an assignment question"""

    assignment = models.ForeignKey(
        verbose_name=_("response"),
        to=Assignment,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    user = models.ForeignKey(
        verbose_name=_("user"),
        to="users.User",
        on_delete=models.PROTECT,
        related_name="assignment_responses",
        blank=True,
        null=True,
    )
    public = models.BooleanField(
        _("public"),
        default=False,
        help_text=_(
            "Publically credit the user who submitted this response in the gallery"
        ),
    )
    ip_address = models.GenericIPAddressField(_("ip address"), blank=True, null=True)
    datetime = models.DateTimeField(_("datetime"), default=timezone.now)
    data = models.ForeignKey(
        verbose_name=_("data"),
        to=Data,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="responses",
    )
    skip = models.BooleanField(_("skip"), default=False)
    # number is only used for multiple_per_page assignment,
    # keeping track of how many times a single user has submitted
    # per data item
    number = models.PositiveSmallIntegerField(_("number"), default=1)
    flag = models.BooleanField(_("flag"), default=False)
    gallery = models.BooleanField(_("gallery"), default=False)

    # edits
    edit_user = models.ForeignKey(
        verbose_name=_("edit user"),
        to="users.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="edited_assignment_responses",
    )
    edit_datetime = models.DateTimeField(_("edit datetime"), null=True, blank=True)

    objects = ResponseQuerySet.as_manager()
    tags = TaggableManager()

    def __str__(self):
        if self.user:
            from_ = str(self.user)
        elif self.ip_address:
            from_ = str(self.ip_address)
        else:
            from_ = "Anonymous"
        return f"Response by {from_} on {self.datetime}"

    def get_values(self, metadata_keys, include_emails=False):
        """Get the values for this response for CSV export"""
        values = [
            self.user.username if self.user else "Anonymous",
            self.public,
            self.datetime.strftime("%Y-%m-%d %H:%M:%S"),
            self.skip,
            self.flag,
            self.gallery,
            ", ".join(self.tags.values_list("name", flat=True)),
        ]
        if include_emails:
            values.insert(1, self.user.email if self.user else "")
        if self.assignment.multiple_per_page:
            values.append(self.number)
        if self.data:
            values.append(self.data.url)
            values.extend(self.data.metadata.get(k, "") for k in metadata_keys)
        field_labels = self.assignment.fields.exclude(
            type__in=fields.STATIC_FIELDS
        ).values_list("label", flat=True)
        field_values = self.get_field_values()
        # ensure exactly one value per field - default to empty string
        # a multivalued field may have no values
        values += [field_values.get(label, "") for label in field_labels]
        return values

    def get_field_values(self):
        """Return a dictionary of field labels to field values
        This handle filtering and aggregating of multivalued fields
        """
        return dict(
            self.values.order_by("field__order")
            # exclude headers and paragraph fields
            .exclude(field__type__in=fields.STATIC_FIELDS)
            # filter out blank values for multivalued fields
            # there might be blank ones to hold original values,
            # and we do not want that in the comma separated list
            .exclude(value="", field__type__in=fields.MULTI_FIELDS)
            # group by field
            .values("field")
            # concat all values for the same field with commas
            .annotate(agg_value=StringAgg("value", ", "))
            # select the concated value
            .values_list("field__label", "agg_value")
        )

    def create_values(self, data):
        """Given the form data, create the values for this response"""
        # these values are passed in the form, but should not have
        # values created for them
        for key in ["data_id", "full_name", "email", "public"]:
            data.pop(key, None)
        for pk, value in data.items():
            value = value if value is not None else ""
            if not isinstance(value, list):
                value = [value]
            for value_item in value:
                try:
                    field = Field.objects.get(assignment=self.assignment, pk=pk)
                    self.values.create(
                        field=field, value=value_item, original_value=value_item
                    )
                except Field.DoesNotExist:
                    pass

    def send_email(self, email):
        """Send an email of this response"""
        metadata = self.assignment.get_metadata_keys()
        text = "\n".join(
            f"{k}: {v}"
            for k, v in zip(
                self.assignment.get_header_values(metadata), self.get_values(metadata)
            )
        )
        text += (
            f"\n{settings.SPOTUS_URL}{self.assignment.get_absolute_url()}"
            "#assignment-responses"
        )
        EmailMessage(
            subject="[Assignment Response] {} by {}".format(
                self.assignment.title, self.user.username if self.user else "Anonymous"
            ),
            body=text,
            from_email="info@muckrock.com",
            to=[email],
            bcc=["diagnostics@muckrock.com"],
        ).send(fail_silently=False)

    class Meta:
        verbose_name = _("assignment response")


class Value(models.Model):
    """A field value for a given response"""

    response = models.ForeignKey(
        verbose_name=_("response"),
        to=Response,
        on_delete=models.CASCADE,
        related_name="values",
    )
    field = models.ForeignKey(
        verbose_name=_("field"),
        to=Field,
        on_delete=models.PROTECT,
        related_name="values",
    )
    value = models.CharField(_("value"), max_length=2000, blank=True)
    original_value = models.CharField(_("original_value"), max_length=2000, blank=True)

    def __str__(self):
        return self.value

    class Meta:
        verbose_name = _("assignment value")
