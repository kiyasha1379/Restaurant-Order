"""The users and roles section: staff accounts, roles and the permission matrix."""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from werkzeug.wrappers import Response

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import permission_required
from restaurant.constants import AccessLevel, PermissionKey
from restaurant.extensions import db
from restaurant.forms.admin_user_forms import RoleForm, StaffForm
from restaurant.language_context import get_active_language, get_translator
from restaurant.models import Role, User
from restaurant.service_factory import make_staff_service
from restaurant.services import (
    DuplicateEmailError,
    LockoutError,
    RoleInUseError,
    StaffService,
    SystemRoleError,
    UnknownRoleError,
    WeakPasswordError,
)

USERS = PermissionKey.USERS
EDIT = AccessLevel.EDIT
MATRIX_LEVELS = (AccessLevel.NONE, AccessLevel.VIEW, AccessLevel.EDIT)
# Money is a yes/no permission: it is "allowed" from VIEW upwards.
MONEY_LEVELS = (AccessLevel.NONE, AccessLevel.VIEW)
ERROR_KEYS = {
    LockoutError: "admin.users.error.lockout",
    SystemRoleError: "admin.users.error.system_role",
    RoleInUseError: "admin.users.error.role_in_use",
    UnknownRoleError: "admin.users.error.unknown_role",
    DuplicateEmailError: "admin.users.error.duplicate_email",
    WeakPasswordError: "admin.users.error.password",
}


def _error_text(error: Exception) -> str:
    """Return the translated message for a refused staff or role change."""
    return get_translator()(ERROR_KEYS.get(type(error), "admin.users.error.unknown_role"))


def _role_choices(service: StaffService) -> list[tuple[int, str]]:
    """Return (id, name) pairs for the role checkboxes."""
    code = get_active_language().code
    return [(role.id, role.name_in(code)) for role in service.list_roles()]


# --- staff accounts ------------------------------------------------------


@admin_blueprint.get("/users")
@permission_required(USERS)
def users() -> str:
    """List the staff accounts with their roles."""
    return render_template("admin/users/list.html", staff=make_staff_service().list_staff())


def _load_user(user_id: int) -> User:
    """Return the staff account or answer 404."""
    user = make_staff_service().get_user(user_id)
    if user is None or not user.roles:
        abort(404)
    return user


@admin_blueprint.get("/users/new")
@permission_required(USERS, EDIT)
def user_new() -> str:
    """Show an empty staff form."""
    form = StaffForm(is_new=True)
    form.set_role_choices(_role_choices(make_staff_service()))
    return render_template("admin/users/user_form.html", form=form, member=None)


@admin_blueprint.get("/users/<int:user_id>")
@permission_required(USERS)
def user_edit(user_id: int) -> str:
    """Show a staff account in the form (read-only without edit access)."""
    service = make_staff_service()
    member = _load_user(user_id)
    form = StaffForm(
        is_new=False,
        data={
            "display_name": member.display_name,
            "role_ids": [role.id for role in member.roles],
            "is_active": member.is_active,
        },
    )
    form.set_role_choices(_role_choices(service))
    return render_template("admin/users/user_form.html", form=form, member=member)


def _save_user(member: User | None) -> Response | str:
    """Validate the staff form and save the account."""
    service = make_staff_service()
    translate = get_translator()
    form = StaffForm(is_new=member is None)
    form.set_role_choices(_role_choices(service))
    if member is not None and member.id == current_user.id and not form.is_active.data:
        form.is_active.errors = [translate("admin.users.error.block_self")]
    elif form.validate_on_submit():
        try:
            if member is None:
                service.create_staff(
                    form.email.data, form.display_name.data, form.password.data, form.role_ids.data
                )
            else:
                service.update_staff(
                    member,
                    form.display_name.data,
                    form.role_ids.data,
                    form.is_active.data,
                    form.password.data or "",
                )
            db.session.commit()
        except (DuplicateEmailError, LockoutError, UnknownRoleError, WeakPasswordError) as error:
            db.session.rollback()
            target = form.email if isinstance(error, DuplicateEmailError) else form.role_ids
            target.errors = [_error_text(error)]
        else:
            flash(translate("admin.saved"), "success")
            return redirect(url_for("admin.users"))
    flash(translate("admin.form_error"), "error")
    return render_template("admin/users/user_form.html", form=form, member=member)


@admin_blueprint.post("/users/new")
@permission_required(USERS, EDIT)
def user_create() -> Response | str:
    """Create a staff account from the form."""
    return _save_user(None)


@admin_blueprint.post("/users/<int:user_id>")
@permission_required(USERS, EDIT)
def user_update(user_id: int) -> Response | str:
    """Save changes to a staff account."""
    return _save_user(_load_user(user_id))


# --- roles ---------------------------------------------------------------


@admin_blueprint.get("/users/roles")
@permission_required(USERS)
def roles() -> str:
    """List the roles with how many people hold each."""
    return render_template("admin/users/roles.html", roles=make_staff_service().list_roles())


def _load_role(role_id: int) -> Role:
    """Return the role or answer 404."""
    role = make_staff_service().get_role(role_id)
    if role is None:
        abort(404)
    return role


def _matrix_rows() -> list[dict]:
    """Return the permissions the matrix lists, each with the levels it offers."""
    return [
        {"key": key, "levels": MONEY_LEVELS if key is PermissionKey.MONEY else MATRIX_LEVELS}
        for key in PermissionKey
    ]


def _levels_from_request() -> dict[PermissionKey, AccessLevel]:
    """Read the matrix from the form: fields `level:<permission>` with none, view or edit."""
    levels = {}
    for row in _matrix_rows():
        try:
            level = AccessLevel(
                request.form.get(f"level:{row['key'].value}", AccessLevel.NONE.value)
            )
        except ValueError:
            level = AccessLevel.NONE
        levels[row["key"]] = level if level in row["levels"] else AccessLevel.NONE
    return levels


def _role_levels(role: Role | None) -> dict[PermissionKey, AccessLevel]:
    """Return the levels a role has now (nothing for a role being created)."""
    if role is None:
        return {}
    return {PermissionKey(grant.permission.key): grant.access_level for grant in role.grants}


def _render_role_form(form: RoleForm, role: Role | None, levels: dict) -> str:
    """Render the role page with the matrix values to show."""
    return render_template(
        "admin/users/role_form.html",
        form=form,
        role=role,
        matrix=_matrix_rows(),
        role_levels=levels,
        members=role.users if role else [],
    )


@admin_blueprint.get("/users/roles/new")
@permission_required(USERS, EDIT)
def role_new() -> str:
    """Show an empty role form."""
    return _render_role_form(RoleForm(), None, {})


@admin_blueprint.get("/users/roles/<int:role_id>")
@permission_required(USERS)
def role_edit(role_id: int) -> str:
    """Show a role with its permission matrix (read-only without edit access)."""
    role = _load_role(role_id)
    form = RoleForm(data={"name_fa": role.name, "name_en": role.name_en})
    return _render_role_form(form, role, _role_levels(role))


def _save_role(role: Role | None) -> Response | str:
    """Validate the role form and save the names and the matrix."""
    service = make_staff_service()
    translate = get_translator()
    form = RoleForm()
    levels = _levels_from_request()
    if form.validate_on_submit():
        try:
            if role is None:
                role = service.create_role(form.name_fa.data, form.name_en.data)
            else:
                service.rename_role(role, form.name_fa.data, form.name_en.data)
            service.save_grants(role, levels)
            db.session.commit()
        except (SystemRoleError, LockoutError) as error:
            db.session.rollback()
            flash(_error_text(error), "error")
            return redirect(url_for("admin.roles"))
        flash(translate("admin.saved"), "success")
        return redirect(url_for("admin.roles"))
    flash(translate("admin.form_error"), "error")
    return _render_role_form(form, role, levels)


@admin_blueprint.post("/users/roles/new")
@permission_required(USERS, EDIT)
def role_create() -> Response | str:
    """Create a role with the matrix from the form."""
    return _save_role(None)


@admin_blueprint.post("/users/roles/<int:role_id>")
@permission_required(USERS, EDIT)
def role_update(role_id: int) -> Response | str:
    """Save the names and the permission matrix of a role."""
    return _save_role(_load_role(role_id))


@admin_blueprint.post("/users/roles/<int:role_id>/delete")
@permission_required(USERS, EDIT)
def role_delete(role_id: int) -> Response:
    """Delete a role nobody holds."""
    try:
        make_staff_service().delete_role(_load_role(role_id))
        db.session.commit()
    except (SystemRoleError, RoleInUseError) as error:
        db.session.rollback()
        flash(_error_text(error), "error")
    else:
        flash(get_translator()("admin.deleted"), "success")
    return redirect(url_for("admin.roles"))
