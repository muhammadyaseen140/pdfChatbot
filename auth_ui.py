"""Sign in, sign up and password-reset pages (email + password only)."""

import time

import streamlit as st

import database as db
from email_service import is_smtp_configured, send_reset_code

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 60

# Extra styles for the auth pages: hide the sidebar and style the forms as cards
AUTH_CSS = """
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stForm"] {
        border: 1px solid rgba(128, 128, 128, 0.3);
        border-radius: 14px;
        padding: 1.5rem;
        background-color: var(--secondary-background-color);
        box-shadow: 0 0 25px var(--grid-glow-color);
    }
    .auth-title { text-align: center; margin-top: 2rem; margin-bottom: 0.2rem; font-size: 2rem; font-weight: 700; }
    .auth-subtitle { text-align: center; opacity: 0.7; margin-bottom: 1.5rem; }
</style>
"""


def _switch_view(view):
    """Change the visible auth page and rerun."""
    st.session_state.auth_view = view
    st.rerun()


def _render_header(subtitle):
    st.markdown("<div class='auth-title'>🤝 Enterprise Knowledge Base</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='auth-subtitle'>{subtitle}</div>", unsafe_allow_html=True)


def _show_notice():
    """Display and clear a one-time message (e.g. after sign up)."""
    notice = st.session_state.pop("auth_notice", None)
    if notice:
        st.success(notice)


def _render_sign_in():
    _render_header("Sign in to your account")
    _show_notice()

    with st.form("signin_form"):
        email = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        remaining = st.session_state.get("login_locked_until", 0) - time.time()
        if remaining > 0:
            st.error(f"Too many failed attempts. Try again in {int(remaining) + 1} seconds.")
        else:
            user = db.authenticate_user(email, password)
            if user:
                st.session_state.failed_logins = 0
                st.session_state.user = user
                st.rerun()
            else:
                st.session_state.failed_logins = st.session_state.get("failed_logins", 0) + 1
                if st.session_state.failed_logins >= MAX_FAILED_LOGINS:
                    st.session_state.login_locked_until = time.time() + LOCKOUT_SECONDS
                    st.session_state.failed_logins = 0
                st.error("Invalid email or password.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Forgot password?", use_container_width=True):
            _switch_view("forgot")
    with col2:
        if st.button("Create account", use_container_width=True):
            _switch_view("signup")


def _render_sign_up():
    _render_header("Create your account")

    with st.form("signup_form"):
        name = st.text_input("Full name")
        email = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password", help="At least 8 characters, with a letter and a number.")
        confirm = st.text_input("Confirm password", type="password")
        accepted = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        submitted = st.form_submit_button("Create account", use_container_width=True)

    if submitted:
        if password != confirm:
            st.error("Passwords do not match.")
        elif not accepted:
            st.error("Please accept the terms to continue.")
        else:
            ok, message = db.create_user(name, email, password)
            if ok:
                st.session_state.auth_notice = "Account created. Please sign in."
                _switch_view("signin")
            else:
                st.error(message)

    if st.button("Already have an account? Sign in", use_container_width=True):
        _switch_view("signin")


def _render_forgot_password():
    _render_header("Reset your password")
    st.caption("Enter your email and we will send you a 6-digit code.")

    with st.form("forgot_form"):
        email = st.text_input("Email", placeholder="you@company.com")
        submitted = st.form_submit_button("Send reset code", use_container_width=True)

    if submitted:
        error = db.validate_email(email)
        if error:
            st.error(error)
        else:
            code = db.create_reset_code(email)
            st.session_state.reset_email = db.normalize_email(email)
            st.session_state.demo_code = None
            if code:
                if is_smtp_configured():
                    if not send_reset_code(st.session_state.reset_email, code):
                        st.error("We could not send the email. Please try again later.")
                        return
                else:
                    # Demo mode: no SMTP configured, so show the code on screen
                    st.session_state.demo_code = code
            # Same message whether or not the account exists (prevents account enumeration)
            st.session_state.auth_notice = "If an account exists for this email, a reset code has been sent."
            _switch_view("reset")

    if st.button("Back to sign in", use_container_width=True):
        _switch_view("signin")


def _render_reset_password():
    _render_header("Enter your reset code")
    _show_notice()

    if st.session_state.get("demo_code"):
        st.warning(
            f"Demo mode (SMTP is not configured). Your reset code is: **{st.session_state.demo_code}**"
        )

    with st.form("reset_form"):
        code = st.text_input("6-digit code")
        new_password = st.text_input("New password", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Update password", use_container_width=True)

    if submitted:
        if new_password != confirm:
            st.error("Passwords do not match.")
        else:
            ok, message = db.reset_password(st.session_state.get("reset_email", ""), code, new_password)
            if ok:
                st.session_state.demo_code = None
                st.session_state.auth_notice = message
                _switch_view("signin")
            else:
                st.error(message)

    if st.button("Back to sign in", use_container_width=True):
        _switch_view("signin")


def render_auth_page():
    """Render the correct auth page in a centered column."""
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    view = st.session_state.get("auth_view", "signin")
    _, center, _ = st.columns([1, 1.4, 1])
    with center:
        if view == "signup":
            _render_sign_up()
        elif view == "forgot":
            _render_forgot_password()
        elif view == "reset":
            _render_reset_password()
        else:
            _render_sign_in()
