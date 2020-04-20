# Django
from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

# SpotUs
from spotus.assignments.viewsets import ResponseViewSet
from spotus.users.api.views import UserViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
router.register("assignment-responses", ResponseViewSet)


app_name = "api"
urlpatterns = router.urls
