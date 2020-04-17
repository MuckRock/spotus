"""
Provides a base email class for messages.
"""

# Django
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

# Third Party
from html2text import html2text


class TemplateEmail(EmailMultiAlternatives):
    """
    The TemplateEmail class provides a base for our transactional emails.  It
    supports sending a templated email to a user and providing extra template
    context.  It always adds a diagnostic email as a BCC'd address.  A HTML
    template should be provided by subclasses or instances.  The summary
    attribute is blank by default and is a hack to populate the "email preview"
    display within some (not all) email clients.  Subjects are expected to be
    provided at initialization, however a subclass may provide a static subject
    attribute if it is provided to the super __init__ method as as kwarg.
    """

    user = None
    html_template = None
    summary = ""

    def __init__(self, user=None, **kwargs):
        """Sets the universal attributes for all our email."""
        # Pop our expected keyword arguments to prevent base class init errors
        extra_context = kwargs.pop("extra_context", None)
        html_template = kwargs.pop("html_template", None)
        summary = kwargs.pop("summary", None)
        # Initialize the base class
        super().__init__(**kwargs)

        # Set the fields for the TemplateEmail
        if user:
            self.user = user
            self.to.append(user.email)
        if summary:
            self.summary = summary
        if html_template:
            self.html_template = html_template

        context = self.get_context_data(extra_context)
        html = render_to_string(self.html_template, context)

        self.bcc.append(settings.DIAGNOSTICS_EMAIL)
        self.body = html2text(html)
        self.attach_alternative(html, "text/html")

    def get_context_data(self, extra_context):
        """Sets basic context data and allow extra context to be passed in."""
        context = {
            "base_url": settings.SPOTUS_URL,
            "summary": self.summary,
            "subject": self.subject,
            "user": self.user,
        }
        if extra_context:
            context.update(extra_context)
        return context
