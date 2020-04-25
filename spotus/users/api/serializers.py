# Django
from rest_framework import serializers

# SpotUs
from spotus.users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "name"]
