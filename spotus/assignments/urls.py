"""
URL mappings for the assignment app
"""

# Django
from django.urls import path

# SpotUs
from spotus.assignments import views

app_name = "assignments"
urlpatterns = [
    path("<slug:slug>-<int:pk>/", views.AssignmentDetailView.as_view(), name="detail"),
    path(
        "<slug:slug>-<int:pk>/draft/",
        views.AssignmentUpdateView.as_view(),
        name="draft",
    ),
    path(
        "<slug:slug>-<int:pk>/form/",
        views.AssignmentFormView.as_view(),
        name="assignment",
    ),
    path(
        "<slug:slug>-<int:pk>/embed/",
        views.AssignmentEmbededFormView.as_view(),
        name="embed",
    ),
    path(
        "confirm/", views.AssignmentEmbededConfirmView.as_view(), name="embed-confirm"
    ),
    path("", views.AssignmentExploreView.as_view(), name="index"),
    path("list/", views.AssignmentListView.as_view(), name="list"),
    path("create/", views.AssignmentCreateView.as_view(), name="create"),
    path("oembed/", views.oembed, name="oembed"),
    path("message/", views.message_response, name="message-response"),
    path(
        "<int:pk>/edit/",
        views.AssignmentEditResponseView.as_view(),
        name="edit-response",
    ),
    path(
        "<int:pk>/revert/",
        views.AssignmentRevertResponseView.as_view(),
        name="revert-response",
    ),
]
