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