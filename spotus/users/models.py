# Third Party
from squarelet_auth.users.models import User as SAUser


class User(SAUser):
    """Use the Squarelet Auth user as is for now"""
