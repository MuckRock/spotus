# Django
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def nbsp(value):
    """Replace spaces with non-breaking spaces"""
    return mark_safe("&nbsp;".join(value.split(" ")))
