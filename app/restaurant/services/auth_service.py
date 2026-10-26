"""Staff sign-in: password hashing and the check of an e-mail and password."""

from dataclasses import dataclass
from enum import StrEnum

from werkzeug.security import check_password_hash, generate_password_hash

from restaurant.constants import MIN_PASSWORD_LENGTH
from restaurant.models import User
from restaurant.repositories import UserRepository
from restaurant.services.access_service import AccessService
from restaurant.timeutils import now_tehran

# Checked when the e-mail is unknown, so a wrong e-mail takes as long as a wrong password.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


class WeakPasswordError(ValueError):
    """The password is shorter than the minimum."""


def hash_password(password: str) -> str:
    """Return a salted scrypt hash of the password. Short passwords are refused."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(f"A password needs at least {MIN_PASSWORD_LENGTH} characters")
    return generate_password_hash(password, method="scrypt")


class LoginOutcome(StrEnum):
    """Why a sign-in attempt succeeded or failed."""

    OK = "ok"
    INVALID = "invalid"
    BLOCKED = "blocked"
    NO_ACCESS = "no_access"


@dataclass(frozen=True)
class LoginResult:
    """The outcome of one sign-in attempt, with the user when it worked."""

    outcome: LoginOutcome
    user: User | None = None


class AuthService:
    """Checks credentials and records successful sign-ins."""

    def __init__(self, user_repository: UserRepository, access_service: AccessService) -> None:
        """Receive the collaborators instead of importing them, so tests can swap them."""
        self._user_repository = user_repository
        self._access_service = access_service

    def authenticate(self, email: str, password: str) -> LoginResult:
        """Check an e-mail and password and decide whether the user may enter the panel."""
        user = self._user_repository.get_by_email(email)
        stored_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH
        password_matches = check_password_hash(stored_hash, password)
        if user is None or not user.password_hash or not password_matches:
            return LoginResult(LoginOutcome.INVALID)
        if not user.is_active:
            return LoginResult(LoginOutcome.BLOCKED)
        if not self._access_service.build_profile(user).has_admin_access:
            return LoginResult(LoginOutcome.NO_ACCESS)
        user.last_login_at = now_tehran()
        return LoginResult(LoginOutcome.OK, user)

    def get_user(self, user_id: int) -> User | None:
        """Return the user with this id, or None (used by the session loader)."""
        return self._user_repository.get(user_id)
