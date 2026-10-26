"""Customer accounts: sign in, register, verify, the account pages and the contact form."""

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from werkzeug.wrappers import Response

from restaurant.account_web import (
    ADDRESS_ERRORS,
    PAGE_SIZE,
    PENDING_SESSION_KEY,
    PROFILE_ERRORS,
    REGISTRATION_ERRORS,
    add_form_error,
    customer_required,
    safe_return_path,
)
from restaurant.blueprints.public import public_blueprint
from restaurant.cart_session import AccountCartStorage, SessionCartStorage
from restaurant.cart_web import is_ordering_paused
from restaurant.extensions import db, limiter
from restaurant.formatting import format_number
from restaurant.forms.account_forms import (
    AddressForm,
    ContactForm,
    PasswordForm,
    ProfileForm,
    RegisterForm,
    SignInForm,
    VerifyForm,
)
from restaurant.language_context import get_active_language, get_translator
from restaurant.models import User
from restaurant.service_factory import (
    make_booking_service,
    make_cart_service,
    make_contact_service,
    make_customer_auth_service,
    make_customer_profile_service,
    make_order_service,
    make_reorder_service,
)
from restaurant.services import (
    AddressInput,
    CodeOutcome,
    ContactError,
    CustomerLoginOutcome,
    ProfileError,
    RegistrationError,
    RegistrationRequest,
)
from restaurant.timeutils import now_tehran

OVERVIEW_ORDERS = 3
OVERVIEW_BOOKINGS = 3
CODE_ERROR_KEYS = {
    CodeOutcome.WRONG: "account.verify.wrong",
    CodeOutcome.EXPIRED: "account.verify.expired",
    CodeOutcome.TOO_MANY: "account.verify.too_many",
}


def _number(value: int) -> str:
    """Write a whole number with the digits of the page language."""
    return format_number(value, get_active_language().code)


def _auth_limit() -> str:
    """Read the sign-in rate limit from the configuration, so tests and servers can change it."""
    return current_app.config["LOGIN_RATE_LIMIT"]


def _contact_limit() -> str:
    """Read the contact-form rate limit from the configuration."""
    return current_app.config["CONTACT_RATE_LIMIT"]


def _finish_sign_in(user: User) -> Response:
    """Sign the customer in, join the saved cart to the current one and go on.

    The cart typed as a guest stays; what the account already held is added to it.
    """
    login_user(user)
    db.session.commit()
    session.pop(PENDING_SESSION_KEY, None)
    make_cart_service().merge_saved(AccountCartStorage.read_saved(user))
    target = safe_return_path(request.values.get("next"))
    return redirect(target or url_for("public.account"))


@public_blueprint.route("/login", methods=["GET", "POST"])
@limiter.limit(_auth_limit, methods=["POST"])
def login() -> Response | str:
    """Show the sign-in form and sign the customer in when the details are right."""
    if current_user.is_authenticated:
        return redirect(safe_return_path(request.args.get("next")) or url_for("public.account"))
    form = SignInForm()
    failure = None
    if form.validate_on_submit():
        result = make_customer_auth_service().authenticate(form.identifier.data, form.password.data)
        if result.outcome is CustomerLoginOutcome.OK:
            return _finish_sign_in(result.user)
        if result.outcome is CustomerLoginOutcome.NEEDS_CODE:
            db.session.commit()
            session[PENDING_SESSION_KEY] = result.user.id
            return redirect(url_for("public.verify", next=request.values.get("next")))
        failure = get_translator()(
            "account.login.error.blocked"
            if result.outcome is CustomerLoginOutcome.BLOCKED
            else "account.login.error.invalid"
        )
    return render_template("account/login.html", form=form, failure=failure)


@public_blueprint.route("/register", methods=["GET", "POST"])
@limiter.limit(_auth_limit, methods=["POST"])
def register() -> Response | str:
    """Show the registration form; a valid one creates a pending account and asks for the code."""
    if current_user.is_authenticated:
        return redirect(url_for("public.account"))
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user = make_customer_auth_service().register(
                RegistrationRequest(
                    name=form.customer_name.data,
                    phone=form.phone.data,
                    email=form.email.data,
                    password=form.password.data,
                )
            )
        except RegistrationError as error:
            db.session.rollback()
            field_name, text_key = REGISTRATION_ERRORS[error.problem]
            add_form_error(form, field_name, text_key)
        else:
            db.session.commit()
            session[PENDING_SESSION_KEY] = user.id
            return redirect(url_for("public.verify", next=request.values.get("next")))
    return render_template("account/register.html", form=form)


@public_blueprint.route("/verify", methods=["GET", "POST"])
@limiter.limit(_auth_limit, methods=["POST"])
def verify() -> Response | str:
    """Ask for the code sent to the phone and finish the registration when it is right."""
    service = make_customer_auth_service()
    user_id = session.get(PENDING_SESSION_KEY)
    user = service.get_pending(user_id) if isinstance(user_id, int) else None
    if user is None:
        return redirect(url_for("public.login"))
    form = VerifyForm()
    if form.validate_on_submit():
        outcome, verified = service.verify(user.id, form.code.data)
        db.session.commit()
        if outcome is CodeOutcome.OK:
            flash(get_translator()("account.verified", name=verified.display_name), "success")
            return _finish_sign_in(verified)
        if outcome is CodeOutcome.NOTHING_PENDING:
            return redirect(url_for("public.login"))
        add_form_error(form, "code", CODE_ERROR_KEYS[outcome])
    return render_template(
        "account/verify.html",
        form=form,
        phone=user.phone,
        demo_code=(
            current_app.config["DEMO_VERIFICATION_CODE"]
            if current_app.config["DEMO_MODE"]
            else None
        ),
    )


@public_blueprint.post("/verify/resend")
@limiter.limit(_auth_limit)
def resend_code() -> Response:
    """Send a fresh code to the phone of the pending registration."""
    service = make_customer_auth_service()
    user_id = session.get(PENDING_SESSION_KEY)
    user = service.get_pending(user_id) if isinstance(user_id, int) else None
    if user is None:
        return redirect(url_for("public.login"))
    service.send_code(user)
    db.session.commit()
    flash(get_translator()("account.verify.resent"), "info")
    return redirect(url_for("public.verify", next=request.values.get("next")))


@public_blueprint.post("/logout")
def logout() -> Response:
    """Sign the customer out and empty the cart of this browser (it stays in the account)."""
    logout_user()
    SessionCartStorage().save([])
    flash(get_translator()("account.signed_out"), "info")
    return redirect(url_for("public.home"))


@public_blueprint.get("/account")
@customer_required
def account() -> str:
    """Show the overview: the latest orders, upcoming bookings and the main address."""
    now = now_tehran()
    orders, order_total = make_order_service().list_for_user(current_user.id, 0, OVERVIEW_ORDERS)
    bookings = [
        booking
        for booking in make_booking_service().list_for_user(current_user.id)
        if booking.starts_at >= now and booking.status.value != "cancelled"
    ]
    addresses = make_customer_profile_service().list_addresses(current_user)
    return render_template(
        "account/overview.html",
        orders=orders,
        order_total=order_total,
        bookings=sorted(bookings, key=lambda booking: booking.starts_at)[:OVERVIEW_BOOKINGS],
        default_address=addresses[0] if addresses else None,
        active="overview",
    )


@public_blueprint.get("/account/orders")
@customer_required
def account_orders() -> str:
    """Show every order of the customer, a page at a time."""
    page = max(request.args.get("page", 1, type=int), 1)
    orders, total = make_order_service().list_for_user(
        current_user.id, (page - 1) * PAGE_SIZE, PAGE_SIZE
    )
    return render_template(
        "account/orders.html",
        orders=orders,
        page=page,
        has_next=page * PAGE_SIZE < total,
        active="orders",
    )


@public_blueprint.post("/account/orders/<public_token>/reorder")
@customer_required
def reorder(public_token: str) -> Response:
    """Copy the lines of a past order into the cart and open the cart."""
    order = make_order_service().find_for_user(current_user.id, public_token)
    if order is None:
        abort(404)
    if is_ordering_paused():
        flash(get_translator()("ordering.paused"), "warning")
        return redirect(url_for("public.account_orders"))
    result = make_reorder_service().reorder(order, make_cart_service(), get_active_language().code)
    translate = get_translator()
    if result.added == 0:
        flash(translate("account.reorder.none"), "warning")
        return redirect(url_for("public.account_orders"))
    flash(translate("account.reorder.done", count=_number(result.added)), "success")
    if result.skipped:
        flash(translate("account.reorder.skipped", count=_number(result.skipped)), "warning")
    return redirect(url_for("public.cart"))


@public_blueprint.get("/account/reservations")
@customer_required
def account_reservations() -> str:
    """Show the customer's bookings: the coming ones first, then the past ones."""
    now = now_tehran()
    bookings = make_booking_service().list_for_user(current_user.id)
    upcoming = [b for b in bookings if b.starts_at >= now and b.status.value != "cancelled"]
    past = [booking for booking in bookings if booking not in upcoming]
    return render_template(
        "account/reservations.html",
        upcoming=sorted(upcoming, key=lambda booking: booking.starts_at),
        past=past,
        active="reservations",
    )


@public_blueprint.route("/account/addresses", methods=["GET", "POST"])
@customer_required
def account_addresses() -> Response | str:
    """List the address book and add an address to it."""
    service = make_customer_profile_service()
    form = AddressForm()
    if form.validate_on_submit():
        try:
            service.add_address(
                current_user,
                AddressInput(form.label.data, form.text.data, form.is_default.data),
            )
        except ProfileError as error:
            db.session.rollback()
            add_form_error(form, *ADDRESS_ERRORS[error.problem])
        else:
            db.session.commit()
            flash(get_translator()("account.addresses.saved"), "success")
            return redirect(url_for("public.account_addresses"))
    return render_template(
        "account/addresses.html",
        addresses=service.list_addresses(current_user),
        form=form,
        active="addresses",
    )


@public_blueprint.route("/account/addresses/<int:address_id>/edit", methods=["GET", "POST"])
@customer_required
def account_address_edit(address_id: int) -> Response | str:
    """Change one saved address."""
    service = make_customer_profile_service()
    address = next((a for a in service.list_addresses(current_user) if a.id == address_id), None)
    if address is None:
        abort(404)
    form = AddressForm(obj=address)
    if form.validate_on_submit():
        try:
            service.update_address(
                current_user,
                address_id,
                AddressInput(form.label.data, form.text.data, form.is_default.data),
            )
        except ProfileError as error:
            db.session.rollback()
            add_form_error(form, *ADDRESS_ERRORS[error.problem])
        else:
            db.session.commit()
            flash(get_translator()("account.addresses.saved"), "success")
            return redirect(url_for("public.account_addresses"))
    return render_template(
        "account/address_edit.html", form=form, address=address, active="addresses"
    )


@public_blueprint.post("/account/addresses/<int:address_id>/delete")
@customer_required
def account_address_delete(address_id: int) -> Response:
    """Remove a saved address."""
    try:
        make_customer_profile_service().delete_address(current_user, address_id)
    except ProfileError:
        db.session.rollback()
        abort(404)
    db.session.commit()
    flash(get_translator()("account.addresses.deleted"), "info")
    return redirect(url_for("public.account_addresses"))


@public_blueprint.post("/account/addresses/<int:address_id>/default")
@customer_required
def account_address_default(address_id: int) -> Response:
    """Make a saved address the main one."""
    try:
        make_customer_profile_service().set_default_address(current_user, address_id)
    except ProfileError:
        db.session.rollback()
        abort(404)
    db.session.commit()
    return redirect(url_for("public.account_addresses"))


def _render_profile(profile_form: ProfileForm, password_form: PasswordForm) -> str:
    """Draw the profile page with the two forms (either may carry errors)."""
    return render_template(
        "account/profile.html",
        profile_form=profile_form,
        password_form=password_form,
        active="profile",
    )


@public_blueprint.route("/account/profile", methods=["GET", "POST"])
@customer_required
def account_profile() -> Response | str:
    """Show and change the customer's name and e-mail."""
    form = ProfileForm(
        data={"customer_name": current_user.display_name, "email": current_user.email or ""}
    )
    if request.method == "POST" and form.validate_on_submit():
        try:
            make_customer_profile_service().update_profile(
                current_user, form.customer_name.data, form.email.data
            )
        except ProfileError as error:
            db.session.rollback()
            add_form_error(form, *PROFILE_ERRORS[error.problem])
        else:
            db.session.commit()
            flash(get_translator()("account.profile.saved"), "success")
            return redirect(url_for("public.account_profile"))
    return _render_profile(form, PasswordForm())


@public_blueprint.post("/account/password")
@customer_required
def account_password() -> Response | str:
    """Change the password after checking the current one."""
    form = PasswordForm()
    if form.validate_on_submit():
        try:
            make_customer_profile_service().change_password(
                current_user, form.current_password.data, form.new_password.data
            )
        except ProfileError as error:
            db.session.rollback()
            add_form_error(form, *PROFILE_ERRORS[error.problem])
        else:
            db.session.commit()
            flash(get_translator()("account.password.changed"), "success")
            return redirect(url_for("public.account_profile"))
    profile_form = ProfileForm(
        data={"customer_name": current_user.display_name, "email": current_user.email or ""}
    )
    return _render_profile(profile_form, form)


@public_blueprint.route("/contact", methods=["GET", "POST"])
@limiter.limit(_contact_limit, methods=["POST"])
def contact() -> Response | str:
    """Show the contact form and store a valid message for the staff."""
    form = ContactForm()
    if request.method == "GET" and current_user.is_authenticated:
        form.customer_name.data = current_user.display_name
        form.contact.data = current_user.phone or current_user.email or ""
    if form.validate_on_submit():
        try:
            make_contact_service().submit(
                form.customer_name.data,
                form.contact.data,
                form.body.data,
                get_active_language().code,
                current_user.id if current_user.is_authenticated else None,
            )
        except ContactError:
            db.session.rollback()
            add_form_error(form, "body", "contact.error.body")
        else:
            db.session.commit()
            flash(get_translator()("contact.sent"), "success")
            return redirect(url_for("public.contact"))
    return render_template("contact.html", form=form)
