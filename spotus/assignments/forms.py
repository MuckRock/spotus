"""Forms for the assignment application"""

# Django
from django import forms
from django.core.validators import URLValidator, validate_email
from django.utils.translation import gettext_lazy as _

# Standard Library
import codecs
import csv
import json
import re

# SpotUs
from spotus.assignments.constants import DOCUMENT_URL_RE, PROJECT_URL_RE
from spotus.assignments.fields import FIELD_DICT
from spotus.assignments.models import Assignment, Data, Response
from spotus.assignments.tasks import datum_per_page, import_doccloud_proj
from spotus.users.models import User


class AssignmentForm(forms.Form):
    """Generic assignment form
    This is initialized with a assignment model which is used to dynamically
    populate the form
    """

    data_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    public = forms.BooleanField(
        label="Publicly credit you",
        help_text=_(
            "When selected, we will note you contributed to the project and list "
            "your name next to responses marked public"
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        assignment = kwargs.pop("assignment")
        datum = kwargs.pop("datum")
        metadata = datum.metadata if datum else None

        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        def sub(text, metadata):
            if text is None:
                return text
            text = re.sub("{\s*", "{", text)
            text = re.sub("\s*}", "}", text)
            return text.format_map(metadata)

        for field in assignment.fields.filter(deleted=False):
            # swap in template tags from metadata
            form_field = field.get_form_field()
            form_field.label = sub(form_field.label, metadata)
            form_field.help_text = sub(form_field.help_text, metadata)
            form_field.initial = sub(form_field.initial, metadata)
            self.fields[str(field.pk)] = form_field
        if user.is_anonymous and assignment.registration != "off":
            required = assignment.registration == "required"
            self.fields["full_name"] = forms.CharField(
                label="Full Name or Handle (Public)", required=required
            )
            self.fields["email"] = forms.EmailField(required=required)
            # XXX newsletter?
            self.fields["newsletter"] = forms.BooleanField(
                initial=True,
                required=False,
                label="Get MuckRock's weekly newsletter with "
                "FOIA news, tips, and more",
            )
        if assignment.ask_public:
            # move public to the end
            self.fields["public"] = self.fields.pop("public")
        else:
            # remove public
            self.fields.pop("public")

    def clean_email(self):
        """Do a case insensitive uniqueness check"""
        # XXX should probably do this on squarelet?
        email = self.cleaned_data["email"]
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                _("User with this email already exists. Please login first.")
            )
        return email

    def clean(self):
        """Must supply both name and email, or neither"""
        data = super().clean()

        if data.get("email") and not data.get("full_name"):
            self.add_error(
                "full_name", _("Name is required if registering with an email")
            )
        if data.get("full_name") and not data.get("email"):
            self.add_error("email", _("Email is required if registering with a name"))


class DataCsvForm(forms.Form):
    """Form for adding data to an assignment using a CSV file"""

    data_csv = forms.FileField(label="Data CSV File")
    doccloud_each_page = forms.BooleanField(
        label=_("Split Documents by Page"),
        help_text=_(
            "Each DocumentCloud URL will be split " "up into one assignment per page"
        ),
        required=False,
    )

    def process_data_csv(self, assignment):
        """Create the assignment data from the uploaded CSV"""
        url_validator = URLValidator()
        data_csv = self.cleaned_data["data_csv"]
        doccloud_each_page = self.cleaned_data["doccloud_each_page"]
        if data_csv:
            # python3 wants csvs decoded
            reader = csv.reader(codecs.iterdecode(data_csv, "utf-8"))
            headers = [h.lower() for h in next(reader)]
            for line in reader:
                data = dict(zip(headers, line))
                url = data.pop("url", "")
                doc_match = DOCUMENT_URL_RE.match(url)
                proj_match = PROJECT_URL_RE.match(url)
                if doccloud_each_page and doc_match:
                    datum_per_page.delay(assignment.pk, doc_match.group("doc_id"), data)
                elif proj_match:
                    import_doccloud_proj.delay(
                        assignment.pk,
                        proj_match.group("proj_id"),
                        data,
                        doccloud_each_page,
                    )
                else:
                    assignment.data.create(url=url, metadata=data)


class AssignmentCreationForm(forms.ModelForm, DataCsvForm):
    """Form for creating an assignment"""

    prefix = "assignment"

    form_json = forms.CharField(widget=forms.HiddenInput(), initial="[]")
    submission_emails = forms.CharField(
        help_text=_("Comma seperated list of emails to send to on submission"),
        required=False,
    )

    class Meta:
        model = Assignment
        fields = (
            "title",
            "description",
            "data_limit",
            "user_limit",
            "registration",
            "form_json",
            "data_csv",
            "multiple_per_page",
            "submission_emails",
            "ask_public",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["data_csv"].required = False

    def clean_form_json(self):
        """Ensure the form JSON is in the correct format"""
        # pylint: disable=too-many-branches
        form_json = self.cleaned_data["form_json"]
        try:
            form_data = json.loads(form_json)
        except ValueError:
            raise forms.ValidationError("Invalid form data: Invalid JSON")
        if not isinstance(form_data, list):
            raise forms.ValidationError("Invalid form data: Not a list")
        if form_data == []:
            raise forms.ValidationError(
                "Having at least one field on the form is required"
            )
        for data in form_data:
            label = data.get("label")
            if not label:
                raise forms.ValidationError("Invalid form data: Missing label")
            required = data.get("required", False)
            if required not in [True, False]:
                raise forms.ValidationError("Invalid form data: Invalid required")
            type_ = data.get("type")
            if not type_:
                raise forms.ValidationError(
                    "Invalid form data: Missing type for {}".format(label)
                )
            if type_ not in FIELD_DICT:
                raise forms.ValidationError(
                    "Invalid form data: Bad type {}".format(type_)
                )
            field = FIELD_DICT[type_]
            if field.accepts_choices and "values" not in data:
                raise forms.ValidationError(
                    "Invalid form data: {} requires choices".format(type_)
                )
            if field.accepts_choices and "values" in data:
                for value in data["values"]:
                    choice_label = value.get("label")
                    if not choice_label:
                        raise forms.ValidationError(
                            "Invalid form data: Missing label for "
                            "choice of {}".format(label)
                        )
                    choice_value = value.get("value")
                    if not choice_value:
                        raise forms.ValidationError(
                            "Invalid form data: Missing value for "
                            "choice {} of {}".format(choice_label, label)
                        )
        return form_json

    def clean_submission_emails(self):
        """Validate the submission emails field"""
        emails = self.cleaned_data["submission_emails"].split(",")
        emails = [e.strip() for e in emails if e.strip()]
        bad_emails = []
        for email in emails:
            try:
                validate_email(email.strip())
            except forms.ValidationError:
                bad_emails.append(email)
        if bad_emails:
            raise forms.ValidationError("Invalid email: %s" % ", ".join(bad_emails))
        return ",".join(emails)


DataFormsetBase = forms.inlineformset_factory(
    Assignment, Data, fields=("url",), extra=1, can_delete=False
)


class DataFormset(DataFormsetBase):
    """Assignment data formset"""

    def save(self, commit=True, doccloud_each_page=False):
        """Apply special cases to Document Cloud URLs"""
        instances = super().save(commit=False)
        return_instances = []
        for instance in instances:
            doc_match = DOCUMENT_URL_RE.match(instance.url)
            proj_match = PROJECT_URL_RE.match(instance.url)
            if doccloud_each_page and doc_match:
                datum_per_page.delay(self.instance.pk, doc_match.group("doc_id"), {})
            elif proj_match:
                import_doccloud_proj.delay(
                    self.instance.pk,
                    proj_match.group("proj_id"),
                    {},
                    doccloud_each_page,
                )
            else:
                return_instances.append(instance)
                if commit:
                    instance.save()
        return return_instances


class MessageResponseForm(forms.Form):
    """Form to message the author of a response"""

    response = forms.ModelChoiceField(
        queryset=Response.objects.all(), widget=forms.HiddenInput()
    )
    subject = forms.CharField()
    body = forms.CharField(widget=forms.Textarea())
