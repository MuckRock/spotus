# Django
from django.contrib import admin
from django.contrib.auth import admin as auth_admin

# SpotUs
from spotus.users.models import User


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):

    list_display = (
        "username",
        "name",
        "email",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    search_fields = ("username", "name", "email")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (("Personal info"), {"fields": ("name", "email")}),
        (
            ("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )
