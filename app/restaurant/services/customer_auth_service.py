"""Customer accounts: registration with a phone code, sign-in and the code check.

Customers and staff share the `users` table. A customer has no role; staff use
`AuthService` for the panel and never pass through this service.
"""

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from werkzeug.security import check_password_hash

from restaurant.constants import MIN_PASSWORD_LENGTH
from restaurant.models import User, VerificationCode
from restaurant.phone import normalize_mobile
from restaurant.repositories import (
    OrderRepository,
    ReservationRepository,
    UserRepository,
    VerificationCodeRepository,
)
from restaurant.services.auth_service import hash_password
from restaurant.services.verification_codes import CodeIssuer
from restaurant.timeutils import now_tehran

CODE_LIFETIME = timedelta(minutes=10)
MAX_CODE_ATTEMPTS = 5
MAX_NAME_LENGTH = 120
MIN_NAME_LENGTH = 2
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Checked when the account is unknown, so a wrong identifier takes as long as a wrong password.
_DUMMY_HASH = hash_password("not-a-real-password")


class RegistrationProblem(StrEnum):
    """Why a registration was refused."""

    BAD_NAME = "bad_name"
    BAD_PHONE = "bad_phone"
    BAD_EMAIL = "bad_email"
    WEAK_PASSWORD = "weak_password"
    PHONE_TAKEN = "phone_taken"
    EMAIL_TAKEN = "email_taken"


class RegistrationError(ValueError):
    """A registration cannot be accepted; `problem` says why."""

    def __init__(self, problem: RegistrationProblem) -> None:
        """Keep the problem for the page to turn into a message."""
        super().__init__(problem.value)
        self.problem = problem


@dataclass(frozen=True)
class RegistrationRequest:
    """What the visitor typed on the registration form."""

    name: str
    phone: str
    email: str
    password: str


class CodeOutcome(StrEnum):
    """What happened when a verification code was typed."""

    OK = "ok"
    WRONG = "wrong"
    EXPIRED = "expired"
    TOO_MANY = "too_many"
    NOTHING_PENDING = "nothing_pending"


class CustomerLoginOutcome(StrEnum):
    """Why a customer sign-in succeeded or failed."""

    OK = "ok"
    INVALID = "invalid"
    BLOCKED = "blocked"
    NEEDS_CODE = "needs_code"


@dataclass(frozen=True)
class CustomerLoginResult:
    """The outcome of one sign-in attempt, with the user when there is one to act on."""

    outcome: CustomerLoginOutcome
    user: User | None = None


class CustomerAuthService:
    """Registers customers, checks their codes and passwords."""

    def __init__(
        self,
        user_repository: UserRepository,
        code_repository: VerificationCodeRepository,
        order_repository: OrderRepository,
        reservation_repository: ReservationRepository,
        code_issuer: CodeIssuer,
        secret_key: str,
    ) -> None:
        """Receive the collaborators instead of importing them, so tests can swap them."""
        self._users = user_repository
        self._codes = code_repository
        self._orders = order_repository
        self._reservations = reservation_repository
        self._issuer = code_issuer
        self._secret_key = secret_key

    def register(self, request: RegistrationRequest) -> User:
        """Create a pending account and send it a code. The caller commits.

        A pending account that was never verified is replaced by a new try with the same phone.
        """
        name = request.name.strip()
        phone = normalize_mobile(request.phone)
        email = request.email.strip().lower()
        if not MIN_NAME_LENGTH <= len(name) <= MAX_NAME_LENGTH:
            raise RegistrationError(RegistrationProblem.BAD_NAME)
        if phone is None:
            raise RegistrationError(RegistrationProblem.BAD_PHONE)
        if email and not _EMAIL_PATTERN.match(email):
            raise RegistrationError(RegistrationProblem.BAD_EMAIL)
        if len(request.password) < MIN_PASSWORD_LENGTH:
            raise RegistrationError(RegistrationProblem.WEAK_PASSWORD)

        user = self._users.get_by_phone(phone)
        if user is not None and not user.registration_pending:
            raise RegistrationError(RegistrationProblem.PHONE_TAKEN)
        other = self._users.get_by_email(email) if email else None
        if other is not None and other is not user:
            raise RegistrationError(RegistrationProblem.EMAIL_TAKEN)

        if user is None:
            user = self._users.add(User(phone=phone))
        user.display_name = name
        user.email = email or None
        user.password_hash = hash_password(request.password)
        user.registration_pending = True
        self._users.flush()
        self.send_code(user)
        return user

    def send_code(self, user: User) -> None:
        """Issue a fresh code to the user's phone and forget the older ones."""
        code = self._issuer.issue(user.phone or "")
        self._codes.delete_for_user(user.id)
        self._codes.add(
            VerificationCode(
                user_id=user.id,
                code_hash=self._hash_code(user.id, code),
                expires_at=now_tehran() + CODE_LIFETIME,
            )
        )

    def verify(self, user_id: int, code: str) -> tuple[CodeOutcome, User | None]:
        """Check a typed code. On success the account becomes active and past guest orders join it.

        The caller commits (a wrong try is stored too, so the attempts add up).
        """
        user = self._users.get(user_id)
        stored = self._codes.latest_for_user(user_id)
        if user is None or not user.registration_pending or stored is None:
            return CodeOutcome.NOTHING_PENDING, None
        if stored.attempts >= MAX_CODE_ATTEMPTS:
            return CodeOutcome.TOO_MANY, None
        if stored.expires_at < now_tehran():
            return CodeOutcome.EXPIRED, None
        stored.attempts += 1
        expected = stored.code_hash
        if not hmac.compare_digest(expected, self._hash_code(user_id, code.strip())):
            return CodeOutcome.WRONG, None
        user.registration_pending = False
        self._codes.delete_for_user(user_id)
        if user.phone:
            self._orders.claim_guest_orders(user.phone, user.id)
            self._reservations.claim_guest_reservations(user.phone, user.id)
        return CodeOutcome.OK, user

    def get_pending(self, user_id: int) -> User | None:
        """Return the user if they still have to type their code, else None."""
        user = self._users.get(user_id)
        return user if user is not None and user.registration_pending else None

    def authenticate(self, identifier: str, password: str) -> CustomerLoginResult:
        """Check a phone number or e-mail with a password.

        A correct password on an account that never typed its code sends a new code.
        """
        user = self._find(identifier)
        stored_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH
        password_matches = check_password_hash(stored_hash, password)
        if user is None or not user.password_hash or not password_matches:
            return CustomerLoginResult(CustomerLoginOutcome.INVALID)
        if user.registration_pending:
            self.send_code(user)
            return CustomerLoginResult(CustomerLoginOutcome.NEEDS_CODE, user)
        if not user.is_active:
            return CustomerLoginResult(CustomerLoginOutcome.BLOCKED)
        user.last_login_at = now_tehran()
        return CustomerLoginResult(CustomerLoginOutcome.OK, user)

    def _find(self, identifier: str) -> User | None:
        """Find an account by e-mail (when it has an @) or by mobile number."""
        identifier = identifier.strip()
        if "@" in identifier:
            return self._users.get_by_email(identifier)
        phone = normalize_mobile(identifier)
        return self._users.get_by_phone(phone) if phone else None

    def _hash_code(self, user_id: int, code: str) -> str:
        """Return a keyed hash of a code, so the database never holds the code itself."""
        message = f"{self._secret_key}:{user_id}:{code}".encode()
        return hashlib.sha256(message).hexdigest()
