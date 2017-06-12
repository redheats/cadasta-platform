from tutelary.backends import Backend as TutelaryBackend
from django.contrib.auth.backends import ModelBackend


class Auth(TutelaryBackend, ModelBackend):
    pass


class RoleAuthorizationBackend(ModelBackend):

    def has_perm(self, user_obj, perm, obj=None):
        if not obj or not hasattr(obj, 'permissions'):
            return False
        return perm in obj.permissions
