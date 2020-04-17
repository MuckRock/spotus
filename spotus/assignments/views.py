"""Views for the assignments app"""

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.db.models.query import Prefetch
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    TemplateView,
    UpdateView,
)
from django.views.generic.detail import BaseDetailView

# Standard Library
from itertools import zip_longest

# Third Party
import requests
from ipware import get_client_ip

# SpotUs
from spotus.assignments.choices import Registration, Status
from spotus.assignments.filters import AssignmentFilterSet
from spotus.assignments.forms import (
    AssignmentCreationForm,
    AssignmentForm,
    DataCsvForm,
    DataFormset,
    MessageResponseForm,
)
from spotus.assignments.models import Assignment, Data, Field, Response, Value
from spotus.assignments.tasks import export_csv
from spotus.core.email import TemplateEmail
from spotus.core.views import FilterListView


class AssignmentExploreView(TemplateView):
    """Provides a space for exploring active assignments"""

    template_name = "assignments/explore.html"

    def get_context_data(self, **kwargs):
        """Data for the explore page"""
        context = super().get_context_data(**kwargs)
        context["assignment_users"] = Response.objects.get_user_count()
        context["assignment_data"] = Response.objects.count()
        context["assignment_count"] = Assignment.objects.exclude(
            status=Status.draft
        ).count()
        context["assignments"] = (
            Assignment.objects.annotate(
                user_count=Count("responses__user", distinct=True)
            )
            .order_by("-datetime_created")
            .filter(status=Status.open, featured=True)
            .select_related("user")
            .prefetch_related(
                "data",
                Prefetch("responses", queryset=Response.objects.select_related("user")),
            )[:5]
        )
        return context


class AssignmentDetailView(DetailView):
    """A view for those with permission to view the particular assignment"""

    template_name = "assignments/detail.html"
    query_pk_and_slug = True
    context_object_name = "assignment"
    queryset = Assignment.objects.select_related("user").prefetch_related(
        "data", "responses"
    )

    def dispatch(self, *args, **kwargs):
        """Redirect to assignment page for those without permission"""
        assignment = self.get_object()
        if not self.request.user.has_perm("assignments.view_assignment", assignment):
            return redirect(
                "assignments:assignment", slug=assignment.slug, pk=assignment.pk
            )
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Handle CSV downloads"""
        assignment = self.get_object()
        has_perm = self.request.user.has_perm(
            "assignments.change_assignment", assignment
        )
        if self.request.GET.get("csv") and has_perm:
            export_csv.delay(assignment.pk, self.request.user.pk)
            messages.info(
                self.request,
                "Your CSV is being processed.  It will be emailed to you when "
                "it is ready.",
            )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Handle actions on the assignment"""
        assignment = self.get_object()
        has_perm = self.request.user.has_perm(
            "assignments.change_assignment", assignment
        )
        if not has_perm:
            messages.error(
                request, "You do not have permission to edit this assignment"
            )
            return redirect(assignment)
        if request.POST.get("action") == "Close":
            assignment.status = "close"
            assignment.save()
            messages.success(request, "The assignment has been closed")
        elif request.POST.get("action") == "Add Data":
            form = DataCsvForm(request.POST, request.FILES)
            if form.is_valid():
                form.process_data_csv(assignment)
                messages.success(request, "The data is being added to the assignment")
            else:
                messages.error(request, form.errors)
        return redirect(assignment)

    def get_context_data(self, **kwargs):
        """Admin link"""
        context = super().get_context_data(**kwargs)
        context["sidebar_admin_url"] = reverse(
            "admin:assignments_assignment_change", args=(self.object.pk,)
        )
        context["message_form"] = MessageResponseForm()
        context["data_form"] = DataCsvForm()
        context["edit_access"] = self.request.user.has_perm(
            "assignments.change_assignment", self.object
        )
        return context


class AssignmentFormView(BaseDetailView, FormView):
    """A view for a user to fill out the assignment form"""

    template_name = "assignments/form.html"
    form_class = AssignmentForm
    query_pk_and_slug = True
    context_object_name = "assignment"
    queryset = Assignment.objects.filter(status__in=[Status.draft, Status.open])
    minireg_source = "Assignment"
    field_map = {"email": "email", "name": "full_name"}

    def dispatch(self, request, *args, **kwargs):
        """Check permissions"""
        # pylint: disable=attribute-defined-outside-init
        self.object = self.get_object()
        edit_perm = request.user.has_perm("assignments.change_assignment", self.object)
        form_perm = request.user.has_perm("assignments.form_assignment", self.object)
        if self.object.status == Status.draft and not edit_perm:
            raise Http404
        if not form_perm:
            messages.error(request, "That assignment is private")
            return redirect("assignments:list")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Cache the object for POST requests"""
        # pylint: disable=attribute-defined-outside-init
        assignment = self.get_object()
        data_id = self.request.POST.get("data_id")
        if data_id:
            self.data = assignment.data.filter(pk=data_id).first()
        else:
            self.data = None

        if assignment.status == Status.draft:
            messages.error(request, "No submitting to draft assignments")
            return redirect(assignment)
        if request.POST.get("submit") == "Skip":
            return self.skip()
        return super().post(request, args, kwargs)

    def get(self, request, *args, **kwargs):
        """Check if there is a valid assignment"""
        ip_address, _ = get_client_ip(self.request)
        has_assignment = self._has_assignment(
            self.get_object(), self.request.user, ip_address
        )
        if has_assignment:
            return super().get(request, args, kwargs)
        else:
            messages.warning(
                request,
                "Sorry, there are no assignments left for you to complete "
                "at this time for that assignment",
            )
            return redirect("assignments:list")

    def _has_assignment(self, assignment, user, ip_address):
        """Check if the user has a valid assignment to complete"""
        # pylint: disable=attribute-defined-outside-init
        if user.is_anonymous:
            user = None
        else:
            ip_address = None
        self.data = assignment.get_data_to_show(user, ip_address)
        if assignment.data.exists():
            return self.data is not None
        else:
            return not (
                assignment.user_limit
                and assignment.responses.filter(
                    user=user, ip_address=ip_address
                ).exists()
            )

    def get_form_kwargs(self):
        """Add the assignment object to the form"""
        kwargs = super().get_form_kwargs()
        kwargs.update({"assignment": self.get_object(), "user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        """Get the data source to show, if there is one"""
        if "data" not in kwargs:
            kwargs["data"] = self.data
        if self.object.multiple_per_page and self.request.user.is_authenticated:
            kwargs["number"] = (
                self.object.responses.filter(
                    user=self.request.user, data=kwargs["data"]
                ).count()
                + 1
            )
        else:
            kwargs["number"] = 1
        return super().get_context_data(**kwargs)

    def get_initial(self):
        """Fetch the assignment data item to show with this form,
        if there is one"""
        if self.request.method == "GET" and self.data is not None:
            return {"data_id": self.data.pk}
        else:
            return {}

    def form_valid(self, form):
        """Save the form results"""
        assignment = self.get_object()
        has_data = assignment.data.exists()
        if self.request.user.is_authenticated:
            user = self.request.user
            ip_address = None
        elif form.cleaned_data.get("email"):
            try:
                user = self.miniregister(
                    form,
                    form.cleaned_data["full_name"],
                    form.cleaned_data["email"],
                    form.cleaned_data.get("newsletter"),
                )
            except requests.exceptions.RequestException:
                return self.form_invalid(form)
            ip_address = None
        else:
            user = None
            ip_address, _ = get_client_ip(self.request)
        if user or ip_address:
            number = (
                self.object.responses.filter(
                    user=user, ip_address=ip_address, data=self.data
                ).count()
                + 1
            )
        else:
            number = 1
        if not has_data or self.data is not None:
            response = Response.objects.create(
                assignment=assignment,
                user=user,
                public=form.cleaned_data.get("public", False),
                ip_address=ip_address,
                data=self.data,
                number=number,
            )
            response.create_values(form.cleaned_data)
            messages.success(self.request, "Thank you!")
            for email in assignment.submission_emails.all():
                response.send_email(email.email)

        if self.request.POST.get("submit") == "Submit and Add Another":
            return self.render_to_response(self.get_context_data(data=self.data))

        if has_data:
            return redirect(
                "assignments:assignment", slug=assignment.slug, pk=assignment.pk
            )
        else:
            return redirect("assignments:list")

    def form_invalid(self, form):
        """Make sure we include the data in the context"""
        return self.render_to_response(self.get_context_data(form=form, data=self.data))

    def skip(self):
        """The user wants to skip this data"""
        assignment = self.get_object()
        ip_address, _ = get_client_ip(self.request)
        can_submit_anonymous = (
            assignment.registration != Registration.required and ip_address
        )
        if self.data is not None and self.request.user.is_authenticated:
            Response.objects.create(
                assignment=assignment, user=self.request.user, data=self.data, skip=True
            )
            messages.info(self.request, "Skipped!")
        elif self.data is not None and can_submit_anonymous:
            Response.objects.create(
                assignment=assignment, ip_address=ip_address, data=self.data, skip=True
            )
            messages.info(self.request, "Skipped!")
        return redirect(
            "assignments:assignment", slug=assignment.slug, pk=assignment.pk
        )

    def miniregister(self, *args, **kwargs):
        # XXX copy mini reg mixin over from muckrock
        raise NotImplementedError


class AssignmentEditResponseView(BaseDetailView, FormView):
    """A view for an admin to edit a submitted response"""

    template_name = "assignments/form.html"
    form_class = AssignmentForm
    context_object_name = "response"
    model = Response

    def dispatch(self, request, *args, **kwargs):
        """Check permissions"""
        # pylint: disable=attribute-defined-outside-init
        self.object = self.get_object()
        edit_perm = request.user.has_perm(
            "assignments.change_assignment", self.object.assignment
        )
        if not edit_perm:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Add the user and assignment object to the form"""
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"assignment": self.get_object().assignment, "user": self.request.user}
        )
        return kwargs

    def get_initial(self):
        """Fetch the assignment data item to show with this form,
        if there is one, and the latest values"""
        return self._get_initial("value")

    def _get_initial(self, value_attr):
        """Helper function to allow overriding of the value attribute for the
        revert view"""
        initial = {"data_id": self.object.data_id}
        for value in self.object.values.exclude(**{value_attr: ""}):
            key = str(value.field.pk)
            if key in initial:
                # if a single field has multiple values, make a list of values
                if isinstance(initial[key], list):
                    initial[key].append(getattr(value, value_attr))
                else:
                    initial[key] = [initial[key], getattr(value, value_attr)]
            else:
                initial[key] = getattr(value, value_attr)
        return initial

    def get_context_data(self, **kwargs):
        """Set the assignment and data in the context"""
        return super().get_context_data(
            assignment=self.object.assignment, data=self.object.data, edit=True
        )

    @transaction.atomic
    def form_valid(self, form):
        """Save the form results"""
        response = self.object
        response.edit_user = self.request.user
        response.edit_datetime = timezone.now()
        response.save()

        # remove non-assignment field fields
        form.cleaned_data.pop("data_id", None)
        form.cleaned_data.pop("public", None)
        for field_id, new_value in form.cleaned_data.iteritems():
            field = Field.objects.filter(pk=field_id).first()
            if field and field.field.multiple_values:
                # for multi valued fields, collect all old and new values together
                # and recreate all values
                original_value = (
                    response.values.filter(field_id=field_id)
                    .exclude(original_value="")
                    .values_list("original_value", flat=True)
                )
                response.values.filter(field_id=field_id).delete()
                for orig, new in zip_longest(original_value, new_value, fillvalue=""):
                    response.values.create(
                        field_id=field_id, value=new, original_value=orig
                    )
            else:
                # for single valued field, just update the current value
                new_value = new_value if new_value is not None else ""
                response.values.update_or_create(
                    field_id=field_id, defaults={"value": new_value}
                )

        return redirect(
            "assignments:detail",
            slug=response.assignment.slug,
            pk=response.assignment.pk,
        )


class AssignmentRevertResponseView(AssignmentEditResponseView):
    """A view for an admin to revert a submitted response to its original values"""

    def get_initial(self):
        """Fetch the assignment data item to show with this form,
        if there is one, and the latest values"""
        return self._get_initial("original_value")


@method_decorator(xframe_options_exempt, name="dispatch")
class AssignmentEmbededFormView(AssignmentFormView):
    """A view to embed an assignment"""

    template_name = "assignments/embed.html"

    def form_valid(self, form):
        """Redirect to embedded confirmation page"""
        super().form_valid(form)
        return redirect("assignments:embed-confirm")


@method_decorator(xframe_options_exempt, name="dispatch")
class AssignmentEmbededConfirmView(TemplateView):
    """Embedded confirm page"""

    template_name = "assignments/embed_confirm.html"


class AssignmentListView(FilterListView):
    """List of crowdfunds"""

    model = Assignment
    template_name = "assignments/list.html"
    sort_map = {"title": "title", "user": "user"}
    filter_class = AssignmentFilterSet

    def get_queryset(self):
        """Get all open assignments and all assignments you own"""
        queryset = super().get_queryset()
        queryset = (
            queryset.select_related("user")
            .prefetch_related("data", "responses")
            .distinct()
        )
        return queryset.get_viewable(self.request.user)

    def get_context_data(self, **kwargs):
        """Remove filter for non-staff users"""
        context_data = super().get_context_data()
        if not self.request.user.is_staff:
            context_data.pop("filter", None)
        return context_data


class AssignmentCreateView(PermissionRequiredMixin, CreateView):
    """Create a assignment"""

    model = Assignment
    form_class = AssignmentCreationForm
    template_name = "assignments/create.html"
    permission_required = "assignments.add_assignment"

    def get_context_data(self, **kwargs):
        """Add the data formset to the context"""
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["data_formset"] = DataFormset(self.request.POST)
        else:
            data["data_formset"] = DataFormset(
                initial=[{"url": self.request.GET.get("initial_data")}]
            )
        return data

    def form_valid(self, form):
        """Save the assignment"""
        if self.request.POST.get("submit") == "start":
            status = Status.open
            msg = "Assignment started"
        else:
            status = Status.draft
            msg = "Assignment created"
        context = self.get_context_data()
        formset = context["data_formset"]
        assignment = form.save(commit=False)
        assignment.slug = slugify(assignment.title)
        assignment.user = self.request.user
        assignment.status = status
        assignment.save()
        form.save_m2m()
        assignment.create_form(form.cleaned_data["form_json"])
        form.process_data_csv(assignment)
        if formset.is_valid():
            formset.instance = assignment
            formset.save(doccloud_each_page=form.cleaned_data["doccloud_each_page"])
        messages.success(self.request, msg)
        return redirect(assignment)


@method_decorator(login_required, name="dispatch")
class AssignmentUpdateView(UpdateView):
    """Update a assignment"""

    model = Assignment
    form_class = AssignmentCreationForm
    template_name = "assignments/create.html"
    query_pk_and_slug = True

    def dispatch(self, request, *args, **kwargs):
        """Check permissions"""
        # pylint: disable=attribute-defined-outside-init
        assignment = self.get_object()
        user_allowed = request.user.has_perm(
            "assignments.change_assignment", assignment
        )
        if not user_allowed:
            messages.error(request, "You may not edit this assignment")
            return redirect(assignment)
        if assignment.status != Status.draft:
            export_csv.delay(assignment.pk, self.request.user.pk)
            messages.info(
                self.request, "A CSV of the results so far will be emailed to you"
            )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Set the form JSON in the initial form data"""
        assignment = self.get_object()
        return {
            "form_json": assignment.get_form_json(),
            "submission_emails": ", ".join(
                str(e) for e in assignment.submission_emails.all()
            ),
        }

    def get_context_data(self, **kwargs):
        """Add the data formset to the context"""
        data = super().get_context_data(**kwargs)
        DataFormset.can_delete = True
        if self.request.POST:
            data["data_formset"] = DataFormset(
                self.request.POST, instance=self.get_object()
            )
        else:
            data["data_formset"] = DataFormset(instance=self.get_object())
        return data

    def form_valid(self, form):
        """Save the assignment"""
        if self.request.POST.get("submit") == "start":
            status = Status.open
            msg = "Assignment started"
        else:
            status = Status.draft
            msg = "Assignment updated"
        context = self.get_context_data()
        formset = context["data_formset"]
        assignment = form.save(commit=False)
        assignment.slug = slugify(assignment.title)
        assignment.status = status
        assignment.save()
        form.save_m2m()
        assignment.create_form(form.cleaned_data["form_json"])
        form.process_data_csv(assignment)
        if formset.is_valid():
            formset.save(doccloud_each_page=form.cleaned_data["doccloud_each_page"])
        messages.success(self.request, msg)
        return redirect(assignment)

    def get_form_kwargs(self):
        """Add user to form kwargs"""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


def oembed(request):
    """AJAX view to get oembed data"""
    if "url" in request.GET:
        data = Data(url=request.GET["url"])
        return HttpResponse(data.embed())
    else:
        return HttpResponseBadRequest()


def message_response(request):
    """AJAX view to send an email to the user of a response"""
    form = MessageResponseForm(request.POST)
    if form.is_valid():
        response = form.cleaned_data["response"]
        if not request.user.has_perm(
            "assignments.change_assignment", response.assignment
        ):
            return JsonResponse({"error": "permission denied"}, status=403)
        if not response.user or not response.user.email:
            return JsonResponse({"error": "no email"}, status=400)
        msg = TemplateEmail(
            subject=form.cleaned_data["subject"],
            from_email="info@muckrock.com",
            reply_to=[request.user.email],
            user=response.user,
            text_template="assignments/email/message_user.txt",
            html_template="assignments/email/message_user.html",
            extra_context={
                "body": form.cleaned_data["body"],
                "assignment": response.assignment,
                "from_user": request.user,
            },
        )
        msg.send()
        return JsonResponse({"status": "ok"})
    else:
        return JsonResponse({"error": "form invalid"}, status=400)
