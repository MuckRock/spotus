# Django
from django import template

register = template.Library()


@register.simple_tag
def page_link(request, page_num):
    """Generates a pagination link that preserves context"""
    query = request.GET.copy()
    query["page"] = page_num
    return "?" + query.urlencode()
