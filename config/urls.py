# Django
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="assignments:index"), name="index"),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("spotus.users.urls", namespace="users")),
    # Your stuff: custom urls includes go here
    path("assignments/", include("spotus.assignments.urls", namespace="assignments")),
    path("accounts/", include("social_django.urls", namespace="social")),
    path("squarelet/", include("squarelet_auth.urls", namespace="squarelet_auth")),
    path(
        "organizations/",
        include(
            "squarelet_auth.organizations.urls",
            namespace="squarelet_auth_organizations",
        ),
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# API URLS
urlpatterns += [
    # API base url
    path("api/", include("config.api_router"))
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
