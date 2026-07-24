from enum import Enum
from app.db.models.user import UserRole


# define which roles can access what
ROLE_HIERARCHY = {
    UserRole.SUPER_ADMIN: 4,
    UserRole.ADMIN: 3,
    UserRole.ATTORNEY: 2,
    UserRole.JUNIOR_ASSOCIATE: 1,
}


def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
    """
    Check if user_role meets or exceeds required_role.
    Super admin can do everything, junior associate can do least.
    """
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)


def can_assign_role(actor_role: UserRole, target_role: UserRole) -> bool:
    """
    True when actor may grant target_role via invite or role update.

    Actors may only grant roles at or below their own level, so an admin
    cannot self-escalate (or escalate peers) to super_admin.
    """
    return ROLE_HIERARCHY.get(actor_role, 0) >= ROLE_HIERARCHY.get(target_role, 0)


def can_manage_user(actor_role: UserRole, target_role: UserRole) -> bool:
    """
    True when actor may change role or deactivate a user with target_role.

    Actors cannot manage accounts strictly above them (e.g. admin vs
    super_admin), which prevents demotion/deactivation of higher roles.
    """
    return ROLE_HIERARCHY.get(actor_role, 0) >= ROLE_HIERARCHY.get(target_role, 0)


# permission sets for common operations
CAN_UPLOAD_DOCUMENTS = [UserRole.SUPER_ADMIN, UserRole.ADMIN]
CAN_MANAGE_USERS = [UserRole.SUPER_ADMIN, UserRole.ADMIN]
CAN_VIEW_AUDIT_LOGS = [UserRole.SUPER_ADMIN, UserRole.ADMIN]
CAN_QUERY = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.ATTORNEY,
    UserRole.JUNIOR_ASSOCIATE,
]
CAN_SUBMIT_FEEDBACK = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.ATTORNEY,
    UserRole.JUNIOR_ASSOCIATE,
]