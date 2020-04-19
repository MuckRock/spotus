# SpotUs
from spotus.assignments.choices import Registration, Status


def choices(request):
    """Add the choices to the template context"""
    return {"Registration": Registration, "Status": Status}
