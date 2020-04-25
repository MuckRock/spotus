# Django
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

# SpotUs
from spotus.users.api.serializers import UserSerializer
from spotus.users.models import User


class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def get_queryset(self):
        return self.queryset.filter(pk=self.request.user.pk)

    @action(detail=False, methods=["GET"])
    def me(self, request):
        # pylint: disable=invalid-name
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)
