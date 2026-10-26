"""Sample staff accounts for the demo, one per default role. Safe to run twice."""

from dataclasses import dataclass

from restaurant.access_defaults import ADMIN_ROLE_KEY
from restaurant.repositories import RoleRepository, UserRepository
from restaurant.services import AccessService, StaffService

# Public on purpose: these accounts exist only in the demo (never in a real installation).
DEMO_STAFF_PASSWORD = "demo-pass-1234"


@dataclass(frozen=True)
class DemoStaffMember:
    """One sample account: e-mail, name and the key of its role."""

    email: str
    display_name: str
    role_key: str


DEMO_STAFF: tuple[DemoStaffMember, ...] = (
    DemoStaffMember("admin@example.com", "Demo Admin", ADMIN_ROLE_KEY),
    DemoStaffMember("manager@example.com", "Demo Manager", "manager"),
    DemoStaffMember("cashier@example.com", "Demo Cashier", "cashier"),
    DemoStaffMember("kitchen@example.com", "Demo Kitchen", "kitchen"),
    DemoStaffMember("viewer@example.com", "Demo Viewer", "viewer"),
)


class DemoStaffSeeder:
    """Creates the default roles and the sample accounts that are missing."""

    def __init__(
        self,
        access_service: AccessService,
        staff_service: StaffService,
        user_repository: UserRepository,
        role_repository: RoleRepository,
    ) -> None:
        """Receive the collaborators instead of importing them, so tests can swap them."""
        self._access = access_service
        self._staff = staff_service
        self._users = user_repository
        self._roles = role_repository

    def seed(self) -> int:
        """Add the default roles and the missing sample accounts; return how many accounts."""
        self._access.ensure_defaults()
        added = 0
        for member in DEMO_STAFF:
            if self._users.get_by_email(member.email) is not None:
                continue
            role = self._roles.get_by_key(member.role_key)
            self._staff.create_staff(
                member.email, member.display_name, DEMO_STAFF_PASSWORD, [role.id]
            )
            added += 1
        return added
