import hashlib
import sqlite3
import streamlit as st
from database import get_conn


# ── Hashing ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


# ── User CRUD ─────────────────────────────────────────────────────────────────

def register_user(username, email, password):
    username = username.strip()
    email = email.strip()

    if not username:
        return False, "Username cannot be empty."
    if "@" not in email:
        return False, "Please enter a valid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    conn = get_conn()
    existing_user = conn.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if existing_user:
        conn.close()
        return False, "Username is already taken."

    existing_email = conn.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    if existing_email:
        conn.close()
        return False, "An account with this email already exists."

    try:
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, hash_password(password))
        )
        conn.commit()
        conn.close()
        return True, "Account created! Please log in."
    except Exception as e:
        conn.close()
        return False, str(e)


def login_user(username, password):
    username = username.strip()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if not row:
        return None, "Username not found."

    user = dict(row)
    if not verify_password(password, user["password_hash"]):
        return None, "Incorrect password."

    return user, f"Welcome back, {username}!"


def get_user_by_id(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Session Management ────────────────────────────────────────────────────────

def init_session():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "auth_page" not in st.session_state:
        st.session_state.auth_page = "login"


def set_user(user_dict):
    st.session_state.user = user_dict


def get_current_user():
    return st.session_state.user


def logout():
    st.session_state.user = None
    st.session_state.auth_page = "login"


def is_logged_in():
    return st.session_state.user is not None


# ── Auth UI ───────────────────────────────────────────────────────────────────

CARD_STYLE = """
<style>
.auth-card {
    background: white;
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
}
.auth-title {
    text-align: center;
    font-size: 2.4rem;
    font-weight: 800;
    margin-bottom: 0;
    color: #1a1a2e;
}
.auth-subtitle {
    text-align: center;
    color: #64748b;
    font-size: 1rem;
    margin-top: 0.2rem;
    margin-bottom: 1.5rem;
}
.auth-heading {
    font-size: 1.4rem;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 1rem;
}
.auth-divider {
    text-align: center;
    color: #94a3b8;
    margin: 1rem 0;
    font-size: 0.9rem;
}
</style>
"""


def show_login_page():
    st.markdown(CARD_STYLE, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<p class="auth-title">🔥 HabitAI</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="auth-subtitle">Track your habits. Predict your future.</p>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<p class="auth-heading">Welcome back</p>', unsafe_allow_html=True)

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", use_container_width=True, type="primary"):
            if username and password:
                user, msg = login_user(username, password)
                if user:
                    set_user(user)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("Please fill in all fields.")

        st.markdown('<p class="auth-divider">───── or ─────</p>', unsafe_allow_html=True)
        st.markdown("Don't have an account?")
        if st.button("Create Account", use_container_width=True):
            st.session_state.auth_page = "register"
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


def show_register_page():
    st.markdown(CARD_STYLE, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<p class="auth-title">🔥 HabitAI</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="auth-subtitle">Track your habits. Predict your future.</p>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<p class="auth-heading">Create your account</p>', unsafe_allow_html=True)

        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

        if st.button("Create Account", use_container_width=True, type="primary"):
            if not username or not email or not password or not confirm:
                st.error("Please fill in all fields.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                success, msg = register_user(username, email, password)
                if success:
                    st.success(msg)
                    if st.button("Go to Login"):
                        st.session_state.auth_page = "login"
                        st.rerun()
                else:
                    st.error(msg)

        st.markdown('<p class="auth-divider">───── or ─────</p>', unsafe_allow_html=True)
        st.markdown("Already have an account?")
        if st.button("Back to Login", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)