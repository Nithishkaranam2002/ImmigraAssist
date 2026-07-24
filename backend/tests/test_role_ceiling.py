"""Role-ceiling guards for admin privilege escalation."""

from app.core.permissions import can_assign_role, can_manage_user
from app.db.models.user import UserRole


def test_admin_cannot_assign_super_admin():
    assert can_assign_role(UserRole.ADMIN, UserRole.SUPER_ADMIN) is False


def test_admin_can_assign_peer_and_lower_roles():
    assert can_assign_role(UserRole.ADMIN, UserRole.ADMIN) is True
    assert can_assign_role(UserRole.ADMIN, UserRole.ATTORNEY) is True
    assert can_assign_role(UserRole.ADMIN, UserRole.JUNIOR_ASSOCIATE) is True


def test_super_admin_can_assign_super_admin():
    assert can_assign_role(UserRole.SUPER_ADMIN, UserRole.SUPER_ADMIN) is True


def test_admin_cannot_manage_super_admin():
    assert can_manage_user(UserRole.ADMIN, UserRole.SUPER_ADMIN) is False


def test_admin_can_manage_peer_and_lower_users():
    assert can_manage_user(UserRole.ADMIN, UserRole.ADMIN) is True
    assert can_manage_user(UserRole.ADMIN, UserRole.ATTORNEY) is True


def test_super_admin_can_manage_super_admin():
    assert can_manage_user(UserRole.SUPER_ADMIN, UserRole.SUPER_ADMIN) is True


def test_attorney_cannot_assign_admin():
    assert can_assign_role(UserRole.ATTORNEY, UserRole.ADMIN) is False
    assert can_assign_role(UserRole.ATTORNEY, UserRole.ATTORNEY) is True
