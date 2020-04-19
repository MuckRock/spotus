# Django
from django import template

register = template.Library()


@register.inclusion_tag("lib/social.html", takes_context=True)
def social(context, title=None, url=None):
    """Template tag to insert a sharing widget. If url is none, use the request path."""
    request = context["request"]
    title = context.get("title", "") if title is None else title
    url = request.path if url is None else url
    url = "https://" + request.get_host() + url
    return {"request": request, "title": title, "url": url}
