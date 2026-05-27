import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from datetime import date, timedelta

from database import (
    init_db, add_habit, get_habits, delete_habit, update_habit,
    toggle_checkin, is_done_today, get_all_checkins, get_checkins_for_habit,
)
from auth import (
    init_session, is_logged_in, get_current_user,
    logout, show_login_page, show_register_page,
)
from ml import build_features, streak_stats, weekly_completion, best_day_of_week

# ── App config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="HabitAI", page_icon="🔥", layout="wide")
init_db()
init_session()

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not is_logged_in():
    if st.session_state.auth_page == "register":
        show_register_page()
    else:
        show_login_page()
    st.stop()

# ── Load user data (MUST be before sidebar) ───────────────────────────────────
user     = get_current_user()
user_id  = user["id"]
habits   = get_habits(user_id)
checkins = get_all_checkins(user_id)

CATEGORIES = ["Health", "Fitness", "Learning", "Mindfulness", "Work", "Social", "Other"]

# ── Session state defaults ────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "Today"
if "expanded_habit" not in st.session_state:
    st.session_state.expanded_habit = None

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }

/* Hide Streamlit chrome */
[data-testid="stToolbar"]    { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"]     { display: none !important; }
#MainMenu                    { display: none !important; }

/* Sidebar background */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 55%, #0f3460 100%) !important;
}
section[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
    padding-top: 1rem !important;
}

/* Sidebar all text */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] strong,
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown p {
    color: #e2e8f0 !important;
}

/* Sidebar ALL buttons — force text visible */
section[data-testid="stSidebar"] .stButton > button {
    color: #cbd5e1 !important;
    background: transparent !important;
    border: none !important;
    text-align: left !important;
    width: 100% !important;
    padding: 9px 14px !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    margin: 1px 0 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.10) !important;
    color: #ffffff !important;
    transform: none !important;
}
/* Logout button */
section[data-testid="stSidebar"] .stButton:last-child > button {
    background: #dc3545 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    margin-top: 4px !important;
}

/* Dividers */
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.15) !important;
    margin: 8px 0 !important;
}

/* Habit cards */
.habit-done {
    background: linear-gradient(135deg, #d4edda, #c3e6cb) !important;
    border-left: 4px solid #28a745 !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    margin: 6px 0 !important;
}
.habit-done * { color: #155724 !important; }
.habit-pending {
    background: #f8f9fa !important;
    border-left: 4px solid #adb5bd !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    margin: 6px 0 !important;
    border: 1px solid #dee2e6 !important;
}
.habit-pending * { color: #495057 !important; }

/* General buttons */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: transform 0.15s !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; }

/* Auth card */
.auth-card {
    background: white !important;
    border-radius: 16px !important;
    padding: 32px !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08) !important;
    border: 1px solid #e2e8f0 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
NAV_ITEMS = [
    ("Today",          "📋  Today"),
    ("Manage Habits",  "➕  Manage Habits"),
    ("Analytics",      "📊  Analytics"),
    ("ML Predictions", "🤖  ML Predictions"),
]

with st.sidebar:
    st.markdown(
        f"<h2 style='color:#ffffff;margin-bottom:2px'>🔥 HabitAI</h2>"
        f"<p style='color:#e2e8f0;font-weight:600;margin:0'>{user['username']}</p>"
        f"<p style='color:#94a3b8;font-size:0.78rem;margin:0 0 6px 0'>{user['email']}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<hr style='border-color:rgba(255,255,255,0.15);margin:6px 0 12px 0'>",
        unsafe_allow_html=True,
    )

    for key, label in NAV_ITEMS:
        active = st.session_state.page == key
        bg     = "rgba(255,255,255,0.15)" if active else "transparent"
        border = "3px solid #60a5fa"      if active else "3px solid transparent"
        fw     = "700"                     if active else "500"
        color  = "#ffffff"                 if active else "#cbd5e1"
        # Styled visible row
        st.markdown(
            f"<div style='background:{bg};border-left:{border};border-radius:0 8px 8px 0;"
            f"padding:9px 16px;margin:2px 0;color:{color};font-size:0.95rem;"
            f"font-weight:{fw};font-family:Plus Jakarta Sans,sans-serif'>{label}</div>",
            unsafe_allow_html=True,
        )
        # Real button (transparent overlay — handles click)
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.markdown(
        "<hr style='border-color:rgba(255,255,255,0.15);margin:12px 0 8px 0'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color:#94a3b8;font-size:0.83rem;margin:3px 0'>"
        f"Habits: <b style='color:#e2e8f0'>{len(habits)}</b></p>"
        f"<p style='color:#94a3b8;font-size:0.83rem;margin:3px 0'>"
        f"Check-ins: <b style='color:#e2e8f0'>{len(checkins)}</b></p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<hr style='border-color:rgba(255,255,255,0.15);margin:8px 0'>",
        unsafe_allow_html=True,
    )
    if st.button("🚪  Logout", use_container_width=True, key="logout_btn"):
        logout()
        st.rerun()

page = st.session_state.page

# ── PAGE 1 — Today ────────────────────────────────────────────────────────────
if page == "Today":
    st.header(f"📋 Today — {date.today().strftime('%A, %d %B %Y')}")

    if not habits:
        st.info("No habits yet. Go to **Manage Habits** to add your first one!")
    else:
        done_count    = sum(1 for h in habits if is_done_today(h["id"]))
        total         = len(habits)
        pct           = int(done_count / total * 100) if total else 0
        total_chk     = len(checkins)
        all_dates     = sorted(set(c["date"] for c in checkins))
        _, best_str   = streak_stats(all_dates)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Done Today",      f"{done_count}/{total}")
        c2.metric("📈 Completion",       f"{pct}%")
        c3.metric("🔢 Total Check-ins",  total_chk)
        c4.metric("🏆 Best Streak",      f"{best_str}d")

        st.progress(pct / 100, text=f"Today's progress: {pct}%")
        st.markdown("### Check off your habits")

        for h in habits:
            done      = is_done_today(h["id"])
            dates     = get_checkins_for_habit(h["id"])
            cur, _    = streak_stats(dates)
            badge     = f"🔥 {cur}d streak" if cur > 0 else "Start today!"
            css_class = "habit-done" if done else "habit-pending"
            cat_col   = "#2d6a4f" if done else "#64748b"

            col0, col1, col2 = st.columns([4, 2, 1])
            with col0:
                st.markdown(
                    f'<div class="{css_class}">'
                    f'<strong style="font-size:1rem">{h["name"]}</strong>'
                    f'&nbsp;&nbsp;<span style="background:rgba(0,0,0,0.08);border-radius:5px;'
                    f'padding:2px 8px;font-size:0.78rem;color:{cat_col}">{h["category"]}</span><br>'
                    f'<small style="font-size:0.82rem">{badge}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                label = "Undo" if done else "Done!"
                if st.button(label, key=f"toggle_{h['id']}"):
                    toggle_checkin(h["id"])
                    st.rerun()

        st.divider()
        st.markdown("### Last 7 days")
        day_cols = st.columns(7)
        for i, col in enumerate(day_cols):
            day           = date.today() - timedelta(days=6 - i)
            done_that_day = any(c["date"] == str(day) for c in checkins)
            is_today      = day == date.today()
            box_bg    = "#28a745"          if done_that_day else "#e9ecef"
            box_color = "#ffffff"          if done_that_day else "#6c757d"
            border    = "2px solid #1a1a2e" if is_today      else "2px solid transparent"
            tick      = "✓"               if done_that_day else ""
            with col:
                st.markdown(
                    f"<div style='text-align:center;padding:4px 0'>"
                    f"<div style='width:36px;height:36px;border-radius:8px;background:{box_bg};"
                    f"border:{border};margin:0 auto;display:flex;align-items:center;"
                    f"justify-content:center;font-size:1.1rem;color:{box_color};font-weight:700'>"
                    f"{tick}</div>"
                    f"<div style='font-size:0.75rem;margin-top:4px;color:#64748b'>"
                    f"{day.strftime('%a')}</div>"
                    f"<div style='font-size:0.75rem;color:#94a3b8'>{day.day}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

# ── PAGE 2 — Manage Habits ────────────────────────────────────────────────────
elif page == "Manage Habits":
    st.header("➕ Manage Habits")

    st.markdown(
        "<div style='background:#f8faff;border:1px solid #e2e8f0;border-radius:12px;"
        "padding:4px 20px 16px 20px;margin-bottom:16px'>"
        "<p style='font-weight:700;font-size:1.05rem;margin:12px 0 8px;color:#1a1a2e'>"
        "Add New Habit</p></div>",
        unsafe_allow_html=True,
    )
    with st.form("add_form"):
        c1, c2, c3 = st.columns(3)
        with c1: new_name = st.text_input("Habit Name")
        with c2: new_cat  = st.selectbox("Category", CATEGORIES)
        with c3: new_goal = st.slider("Goal per week", 1, 7, 5)
        if st.form_submit_button("Add Habit", use_container_width=True):
            ok, msg = add_habit(user_id, new_name, new_cat, new_goal)
            if ok:
                st.success(msg); st.rerun()
            else:
                st.error(msg)

    st.divider()
    st.markdown("### Your Habits")

    if not habits:
        st.info("No habits yet. Add one above!")
    else:
        for h in habits:
            dates       = get_checkins_for_habit(h["id"])
            cur, best   = streak_stats(dates)
            total_h     = len(dates)
            is_expanded = st.session_state.expanded_habit == h["id"]

            hcol1, hcol2 = st.columns([6, 1])
            with hcol1:
                st.markdown(
                    f"<div style='background:#f8faff;border:1px solid #e2e8f0;"
                    f"border-radius:10px;padding:14px 18px;margin-bottom:4px'>"
                    f"<span style='font-weight:700;font-size:1rem;color:#1a1a2e'>{h['name']}</span>"
                    f"&nbsp;&nbsp;<span style='background:#e2e8f0;border-radius:6px;padding:2px 10px;"
                    f"font-size:0.8rem;color:#475569'>{h['category']}</span>"
                    f"&nbsp;&nbsp;<span style='font-size:0.85rem;color:#64748b'>"
                    f"🔥 {cur}d &nbsp;🏆 {best}d &nbsp;📅 {total_h} check-ins</span></div>",
                    unsafe_allow_html=True,
                )
            with hcol2:
                if st.button("Hide" if is_expanded else "Edit",
                             key=f"tog_{h['id']}"):
                    st.session_state.expanded_habit = None if is_expanded else h["id"]
                    st.rerun()

            if is_expanded:
                left, right = st.columns([3, 1])
                with left:
                    with st.form(f"edit_{h['id']}"):
                        e_name = st.text_input("Name", value=h["name"])
                        e_cat  = st.selectbox(
                            "Category", CATEGORIES,
                            index=CATEGORIES.index(h["category"])
                            if h["category"] in CATEGORIES else 0,
                        )
                        e_goal = st.slider("Goal per week", 1, 7, int(h["goal_per_week"]))
                        if st.form_submit_button("Save Changes", use_container_width=True):
                            update_habit(h["id"], e_name, e_cat, e_goal)
                            st.session_state.expanded_habit = None
                            st.success("Updated!")
                            st.rerun()
                with right:
                    st.markdown(
                        f"<div style='background:#f8faff;border:1px solid #e2e8f0;"
                        f"border-radius:10px;padding:16px'>"
                        f"<p style='margin:4px 0'><b>Total:</b> {total_h} check-ins</p>"
                        f"<p style='margin:4px 0'><b>Current:</b> 🔥 {cur}d</p>"
                        f"<p style='margin:4px 0'><b>Best:</b> 🏆 {best}d</p>"
                        f"<p style='margin:4px 0'><b>Goal:</b> {h['goal_per_week']}x/week</p>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown("")
                    if st.button("🗑 Delete", key=f"del_{h['id']}",
                                 type="secondary", use_container_width=True):
                        delete_habit(h["id"])
                        st.session_state.expanded_habit = None
                        st.rerun()

    st.divider()
    st.markdown("### Log a Past Check-in")
    if not habits:
        st.info("Add a habit first.")
    else:
        with st.form("past_checkin_form"):
            habit_names = [h["name"] for h in habits]
            sel_name    = st.selectbox("Habit", habit_names)
            sel_date    = st.date_input("Date", max_value=date.today())
            if st.form_submit_button("Log Check-in"):
                sel_h = next(h for h in habits if h["name"] == sel_name)
                toggle_checkin(sel_h["id"], str(sel_date))
                st.success(f"Logged **{sel_name}** on {sel_date}!")
                st.rerun()

# ── PAGE 3 — Analytics ────────────────────────────────────────────────────────
elif page == "Analytics":
    st.header("📊 Analytics")

    if not checkins:
        st.info("No check-ins yet. Start tracking your habits!")
    else:
        df = pd.DataFrame(checkins)
        df["date"] = pd.to_datetime(df["date"])

        all_dates            = sorted(set(c["date"] for c in checkins))
        cur_streak, best_str = streak_stats(all_dates)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Total Check-ins",  len(checkins))
        c2.metric("🗂 Habits Tracked",   len(habits))
        c3.metric("🔥 Current Streak",   f"{cur_streak}d")
        c4.metric("🏆 Best Streak",       f"{best_str}d")

        st.divider()
        cl, cr = st.columns(2)

        with cl:
            st.markdown("### Completions per Habit")
            hc = df.groupby("name").size().sort_values()
            fig, ax = plt.subplots(figsize=(6, max(3, len(hc) * 0.6)))
            ax.set_facecolor("#f8faff"); fig.patch.set_facecolor("#f8faff")
            colors = plt.cm.viridis([i / max(len(hc), 1) for i in range(len(hc))])
            bars = ax.barh(hc.index, hc.values, color=colors)
            ax.bar_label(bars, padding=4, fontsize=9)
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False); ax.set_xlabel("Check-ins")
            plt.tight_layout(); st.pyplot(fig); plt.close()

        with cr:
            st.markdown("### Completion by Day of Week")
            df["dow"]   = df["date"].dt.day_name()
            day_order   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            short_lbl   = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            dow_counts  = df["dow"].value_counts().reindex(day_order, fill_value=0)
            fig2, ax2   = plt.subplots(figsize=(6, 4))
            ax2.set_facecolor("#f8faff"); fig2.patch.set_facecolor("#f8faff")
            ax2.bar(short_lbl, dow_counts.values, color=sns.color_palette("coolwarm", 7))
            ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)
            ax2.set_ylabel("Check-ins")
            plt.tight_layout(); st.pyplot(fig2); plt.close()

        st.divider()
        st.markdown("### Weekly Completion Heatmap (last 8 weeks)")
        pivot = weekly_completion(checkins)
        if not pivot.empty:
            last8      = pivot.tail(8)
            fig3, ax3  = plt.subplots(figsize=(12, max(3, len(last8.columns) * 0.5 + 1)))
            fig3.patch.set_facecolor("#f8faff"); ax3.set_facecolor("#f8faff")
            sns.heatmap(last8.T, annot=True, fmt="d", cmap="YlGn",
                        linewidths=0.5, ax=ax3)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout(); st.pyplot(fig3); plt.close()

        st.divider()
        cl2, cr2 = st.columns(2)

        with cl2:
            st.markdown("### Check-ins by Category")
            cat_counts = df.groupby("category").size()
            fig4, ax4  = plt.subplots(figsize=(5, 4))
            fig4.patch.set_facecolor("#f8faff")
            ax4.pie(cat_counts.values, labels=cat_counts.index,
                    colors=sns.color_palette("Set2", len(cat_counts)),
                    autopct="%1.0f%%", startangle=90)
            plt.tight_layout(); st.pyplot(fig4); plt.close()

        with cr2:
            st.markdown("### Streak Leaderboard")
            board = []
            for h in habits:
                dh = get_checkins_for_habit(h["id"])
                ch, bh = streak_stats(dh)
                board.append({"Habit": h["name"], "Current 🔥": ch,
                              "Best 🏆": bh, "Total": len(dh)})
            ldf = pd.DataFrame(board).sort_values("Best 🏆", ascending=False)
            st.dataframe(ldf, use_container_width=True, hide_index=True)

# ── PAGE 4 — ML Predictions ───────────────────────────────────────────────────
elif page == "ML Predictions":
    st.header("🤖 ML Predictions")
    st.markdown("*Logistic Regression model trained on your personal check-in history.*")

    if not habits:
        st.info("Add habits and check in for a few days to unlock ML predictions!")
    else:
        sel_name  = st.selectbox("Choose a habit", [h["name"] for h in habits])
        days_ahead = st.slider("Days ahead to predict", 3, 14, 7)

        sel_h   = next(h for h in habits if h["name"] == sel_name)
        dates   = get_checkins_for_habit(sel_h["id"])
        cur_s, best_s = streak_stats(dates)

        c1, c2, c3 = st.columns(3)
        c1.metric("📅 Total Check-ins", len(dates))
        c2.metric("🔥 Current Streak",  f"{cur_s}d")
        c3.metric("🏆 Best Streak",     f"{best_s}d")

        st.divider()
        dow = best_day_of_week(dates)
        if any(v > 0 for v in dow.values()):
            best_day = max(dow, key=dow.get)
            st.markdown(
                f"📅 Your **best day** for *{sel_name}* is **{best_day}** "
                f"with {dow[best_day]} check-ins."
            )
            fig5, ax5 = plt.subplots(figsize=(7, 3))
            ax5.set_facecolor("#f8faff"); fig5.patch.set_facecolor("#f8faff")
            ax5.bar(list(dow.keys()), list(dow.values()),
                    color=["#28a745" if d == best_day else "#adb5bd" for d in dow.keys()])
            ax5.set_ylabel("Check-ins"); ax5.set_title("Completions by day of week")
            ax5.spines["top"].set_visible(False); ax5.spines["right"].set_visible(False)
            plt.tight_layout(); st.pyplot(fig5); plt.close()

        st.divider()
        st.markdown("### Predicted completion probability")
        pred_df, err = build_features(dates, days_ahead)

        if err:
            st.warning(err)
        else:
            bar_colors = [
                "#28a745" if p >= 70 else "#fd7e14" if p >= 40 else "#dc3545"
                for p in pred_df["probability"]
            ]
            x_labels = [date.fromisoformat(d).strftime("%b %d")
                        for d in pred_df["date"]]

            fig6, ax6 = plt.subplots(figsize=(10, 4))
            ax6.set_facecolor("#f8faff"); fig6.patch.set_facecolor("#f8faff")
            ax6.bar(x_labels, pred_df["probability"], color=bar_colors)
            ax6.axhline(70, color="#28a745", linestyle="--", alpha=0.6, linewidth=1.5)
            ax6.axhline(40, color="#fd7e14", linestyle="--", alpha=0.6, linewidth=1.5)
            ax6.legend(handles=[
                mpatches.Patch(color="#28a745", label="High (≥70%)"),
                mpatches.Patch(color="#fd7e14", label="Medium (40–69%)"),
                mpatches.Patch(color="#dc3545", label="Low (<40%)"),
            ], loc="upper right")
            ax6.set_ylabel("Probability (%)"); ax6.set_ylim(0, 110)
            ax6.spines["top"].set_visible(False); ax6.spines["right"].set_visible(False)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout(); st.pyplot(fig6); plt.close()

            def likelihood(p):
                return "🟢 High" if p >= 70 else ("🟡 Medium" if p >= 40 else "🔴 Low")

            disp = pred_df.copy()
            disp.columns = ["Date", "Probability (%)"]
            disp["Likelihood"] = disp["Probability (%)"].apply(likelihood)
            st.dataframe(disp, use_container_width=True, hide_index=True)

            avg = pred_df["probability"].mean()
            if avg >= 70:
                st.success(f"✅ Strong week ahead! Average: {avg:.1f}%")
            elif avg >= 40:
                st.warning(f"⚠️ Moderate week. Average: {avg:.1f}% — stay consistent!")
            else:
                st.error(f"🔴 Challenging week predicted: {avg:.1f}% — try to build momentum!")