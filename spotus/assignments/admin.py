"""Admin configuration for the Assignments app"""

# Django
from django.contrib import admin
from django.urls import reverse

# SpotUs
from spotus.assignments.models import Assignment, Choice, Field, Response, Value


class FieldInline(admin.TabularInline):
    """Assignment Field inline options"""

    model = Field
    show_change_link = True


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """Assignment admin options"""

    prepopulated_fields = {"slug": ("title",)}
    inlines = (FieldInline,)
    list_display = ("title", "user", "datetime_created", "status", "featured")
    list_filter = ("status", "featured")
    date_hierarchy = "datetime_created"
    search_fields = ("title", "description")
    autocomplete_fields = ("user",)
    save_on_top = True


class ChoiceInline(admin.TabularInline):
    """Assignment Choice inline options"""

    model = Choice


class AssignmentLinkMixin:
    """Add an assignment link which can be used as a field in the admin"""

    def assignment_link(self, obj):
        """Link back to the assignment page"""
        link = reverse("admin:assignments_assignment_change", args=(obj.assignment.pk,))
        return f'<a href="{link}">{obj.assignment.title}</a>'

    assignment_link.allow_tags = True
    assignment_link.short_description = "Assignment"


@admin.register(Field)
class FieldAdmin(AssignmentLinkMixin, admin.ModelAdmin):
    """Assignment field options"""

    inlines = (ChoiceInline,)
    fields = ("assignment_link", "label", "type", "order")
    readonly_fields = ("assignment_link",)


class ValueInline(admin.TabularInline):
    """Assignment Value inline options"""

    model = Value


@admin.register(Response)
class ResponseAdmin(AssignmentLinkMixin, admin.ModelAdmin):
    """Assignment response options"""

    inlines = (ValueInline,)
    fields = ("assignment_link", "user", "datetime", "data")
    readonly_fields = ("assignment_link", "data")
    autocomplete_fields = ("user",)
