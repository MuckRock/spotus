"""Rules based permissions for the assignment app"""

# pylint: disable=missing-docstring
# pylint: disable=unused-argument

# Third Party
from rules import add_perm, always_allow, always_deny, is_staff, predicate


@predicate
def is_owner(user, assignment):
    if not assignment:
        return None
    return assignment.user == user


@predicate
def has_gallery(user, assignment):
    if not assignment:
        return None
    return assignment.fields.filter(gallery=True).exists()


is_assignment_admin = is_owner | is_staff

can_view = has_gallery | is_assignment_admin

add_perm("assignments.add_assignment", always_allow)
add_perm("assignments.change_assignment", is_assignment_admin)
add_perm("assignments.view_assignment", can_view)
add_perm("assignments.delete_assignment", always_deny)
add_perm("assignments.form_assignment", always_allow)


def assignment_perm(perm):
    @predicate("assignment_perm:{}".format(perm))
    def inner(user, response):
        return user.has_perm(
            "assignments.{}_assignment".format(perm), response.assignment
        )

    return inner


@predicate
def is_gallery(user, response):
    if not response:
        return None
    return response.gallery


add_perm("assignments.add_response", always_allow)
add_perm("assignments.change_esponse", assignment_perm("change"))
add_perm("assignments.view_response", is_gallery | assignment_perm("change"))
add_perm("assignments.delete_response", always_deny)
