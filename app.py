import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from datetime import date, timedelta, datetime

from database import (
    init_db, add_habit, get_habits, delete_habit, update_habit,
    toggle_checkin, is_done_today, get_all_checkins, get_checkins_for_habit,
    log_steps, get_steps_today, get_steps_history, get_steps_all, delete_steps_entry,
    log_water, get_water_today, get_water_history, get_water_all, delete_water_entry,
    log_sleep, get_sleep_today, get_sleep_history, get_sleep_all, delete_sleep_entry,
    log_weight, get_weight_today, get_weight_history, get_weight_all,
    get_latest_weight, delete_weight_entry,
)
from auth import (
    init_session, is_logged_in, get_current_user,
    logout, show_login_page, show_register_page,
)
from ml import build_features, streak_stats, weekly_completion, best_day_of_week

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="HabitAI", page_icon="🔥", layout="wide")
init_db()
init_session()

if not is_logged_in():
    if st.session_state.auth_page == "register":
        show_register_page()
    else:
        show_login_page()
    st.stop()

# ── Data ──────────────────────────────────────────────────────────────────────
user     = get_current_user()
user_id  = user["id"]
habits   = get_habits(user_id)
checkins = get_all_checkins(user_id)
CATEGORIES = ["Health","Fitness","Learning","Mindfulness","Work","Social","Other"]

if "page"           not in st.session_state: st.session_state.page           = "Today"
if "expanded_habit" not in st.session_state: st.session_state.expanded_habit = None

# ── Helpers ───────────────────────────────────────────────────────────────────
def donut_chart(value, total, color, label, unit="", size=3.5):
    """Reusable donut ring chart. Returns fig."""
    pct    = min(value / total * 100, 100) if total > 0 else 0
    remain = max(0, 100 - pct)
    fig, ax = plt.subplots(figsize=(size, size))
    fig.patch.set_facecolor("#f8faff")
    ax.set_facecolor("#f8faff")
    ax.pie(
        [pct, remain],
        colors=[color, "#e9ecef"],
        startangle=90, counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "#f8faff", "linewidth": 3},
    )
    ax.text(0,  0.12, f"{value}{unit}", ha="center", va="center",
            fontsize=18, fontweight="bold", color="#1a1a2e")
    ax.text(0, -0.18, label,            ha="center", va="center",
            fontsize=10, color="#64748b")
    ax.text(0, -0.46, f"{pct:.0f}% of goal", ha="center", va="center",
            fontsize=9, color=color, fontweight="600")
    ax.set_aspect("equal")
    plt.tight_layout()
    return fig

def hydration_streak(user_id):
    """Count consecutive days user met water goal."""
    entries = get_water_all(user_id)
    streak  = 0
    check   = date.today()
    done    = {e["date"] for e in entries if e["glasses"] >= e["goal"]}
    while str(check) in done:
        streak += 1
        check  -= timedelta(days=1)
    return streak

def sleep_streak(user_id):
    """Consecutive nights with 7–9 hrs sleep."""
    entries = get_sleep_all(user_id)
    streak  = 0
    check   = date.today()
    good    = {e["date"] for e in entries if 7 <= e["hours_slept"] <= 9}
    while str(check) in good:
        streak += 1
        check  -= timedelta(days=1)
    return streak

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif !important;}

[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stHeader"],#MainMenu{display:none !important;}

section[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#1a1a2e 0%,#16213e 55%,#0f3460 100%) !important;}
section[data-testid="stSidebar"]>div:first-child{
    background:transparent !important;padding-top:1rem !important;}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] strong,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] .stMarkdown p{color:#e2e8f0 !important;}
section[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,0.15) !important;}
section[data-testid="stSidebar"] .stButton>button{
    color:#cbd5e1 !important;background:transparent !important;border:none !important;
    text-align:left !important;width:100% !important;padding:9px 14px !important;
    font-size:0.95rem !important;font-weight:500 !important;border-radius:8px !important;
    margin:1px 0 !important;}
section[data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(255,255,255,0.10) !important;color:#ffffff !important;transform:none !important;}

.habit-done{background:linear-gradient(135deg,#d4edda,#c3e6cb) !important;
    border-left:4px solid #28a745 !important;border-radius:8px !important;
    padding:12px 16px !important;margin:6px 0 !important;}
.habit-done *{color:#155724 !important;}
.habit-pending{background:#f8f9fa !important;border-left:4px solid #adb5bd !important;
    border-radius:8px !important;padding:12px 16px !important;margin:6px 0 !important;
    border:1px solid #dee2e6 !important;}
.habit-pending *{color:#495057 !important;}

.stat-card{background:#f8faff;border:1px solid #e2e8f0;border-radius:12px;
    padding:16px 20px;margin:4px 0;text-align:center;}
.water-glass{font-size:1.6rem;cursor:pointer;transition:transform 0.1s;}
.water-glass:hover{transform:scale(1.2);}

.stButton>button{border-radius:8px !important;font-weight:600 !important;transition:transform 0.15s !important;}
.stButton>button:hover{transform:translateY(-1px) !important;}
.auth-card{background:white !important;border-radius:16px !important;padding:32px !important;
    box-shadow:0 4px 24px rgba(0,0,0,0.08) !important;border:1px solid #e2e8f0 !important;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
NAV_ITEMS = [
    ("Today",          "📋  Today"),
    ("Manage Habits",  "➕  Manage Habits"),
    ("Analytics",      "📊  Analytics"),
    ("ML Predictions", "🤖  ML Predictions"),
    ("Steps Tracker",  "👟  Steps Tracker"),
    ("Water Tracker",  "💧  Water Tracker"),
    ("Sleep Tracker",  "😴  Sleep Tracker"),
    ("Weight Tracker", "⚖️  Weight Tracker"),
]

with st.sidebar:
    st.markdown(
        f"<h2 style='color:#ffffff;margin-bottom:2px'>🔥 HabitAI</h2>"
        f"<p style='color:#e2e8f0;font-weight:600;margin:0'>{user['username']}</p>"
        f"<p style='color:#94a3b8;font-size:0.78rem;margin:0 0 6px 0'>{user['email']}</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border-color:rgba(255,255,255,0.15);margin:6px 0 10px 0'>",
                unsafe_allow_html=True)

    for key, label in NAV_ITEMS:
        active = st.session_state.page == key
        bg     = "rgba(255,255,255,0.15)" if active else "transparent"
        border = "3px solid #60a5fa"      if active else "3px solid transparent"
        fw     = "700" if active else "500"
        color  = "#ffffff" if active else "#cbd5e1"
        st.markdown(
            f"<div style='background:{bg};border-left:{border};border-radius:0 8px 8px 0;"
            f"padding:9px 16px;margin:2px 0;color:{color};font-size:0.92rem;"
            f"font-weight:{fw};font-family:Plus Jakarta Sans,sans-serif'>{label}</div>",
            unsafe_allow_html=True,
        )
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.markdown("<hr style='border-color:rgba(255,255,255,0.15);margin:10px 0 6px 0'>",
                unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:#94a3b8;font-size:0.83rem;margin:3px 0'>"
        f"Habits: <b style='color:#e2e8f0'>{len(habits)}</b></p>"
        f"<p style='color:#94a3b8;font-size:0.83rem;margin:3px 0'>"
        f"Check-ins: <b style='color:#e2e8f0'>{len(checkins)}</b></p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border-color:rgba(255,255,255,0.15);margin:6px 0'>",
                unsafe_allow_html=True)
    if st.button("🚪  Logout", use_container_width=True, key="logout_btn"):
        logout(); st.rerun()

page = st.session_state.page

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — TODAY
# ═════════════════════════════════════════════════════════════════════════════
if page == "Today":
    st.header(f"📋 Today — {date.today().strftime('%A, %d %B %Y')}")

    if not habits:
        st.info("No habits yet. Go to **Manage Habits** to add your first one!")
    else:
        done_count  = sum(1 for h in habits if is_done_today(h["id"]))
        total       = len(habits)
        pct         = int(done_count / total * 100) if total else 0
        all_dates   = sorted(set(c["date"] for c in checkins))
        _, best_str = streak_stats(all_dates)

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("✅ Done Today",     f"{done_count}/{total}")
        c2.metric("📈 Completion",      f"{pct}%")
        c3.metric("🔢 Total Check-ins", len(checkins))
        c4.metric("🏆 Best Streak",     f"{best_str}d")
        st.progress(pct / 100, text=f"Today's progress: {pct}%")

        st.markdown("### Check off your habits")
        for h in habits:
            done      = is_done_today(h["id"])
            dates     = get_checkins_for_habit(h["id"])
            cur, _    = streak_stats(dates)
            badge     = f"🔥 {cur}d streak" if cur > 0 else "Start today!"
            css_class = "habit-done" if done else "habit-pending"
            cat_col   = "#2d6a4f" if done else "#64748b"
            col0,_,col2 = st.columns([4,2,1])
            with col0:
                st.markdown(
                    f'<div class="{css_class}"><strong style="font-size:1rem">{h["name"]}</strong>'
                    f'&nbsp;&nbsp;<span style="background:rgba(0,0,0,0.08);border-radius:5px;'
                    f'padding:2px 8px;font-size:0.78rem;color:{cat_col}">{h["category"]}</span><br>'
                    f'<small style="font-size:0.82rem">{badge}</small></div>',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("Undo" if done else "Done!", key=f"toggle_{h['id']}"):
                    toggle_checkin(h["id"]); st.rerun()

        st.divider()
        st.markdown("### Last 7 days")
        day_cols = st.columns(7)
        for i, col in enumerate(day_cols):
            day           = date.today() - timedelta(days=6 - i)
            done_that_day = any(c["date"] == str(day) for c in checkins)
            is_today      = day == date.today()
            box_bg    = "#28a745" if done_that_day else "#e9ecef"
            box_color = "#ffffff" if done_that_day else "#6c757d"
            border    = "2px solid #1a1a2e" if is_today else "2px solid transparent"
            with col:
                st.markdown(
                    f"<div style='text-align:center;padding:4px 0'>"
                    f"<div style='width:36px;height:36px;border-radius:8px;background:{box_bg};"
                    f"border:{border};margin:0 auto;display:flex;align-items:center;"
                    f"justify-content:center;font-size:1.1rem;color:{box_color};font-weight:700'>"
                    f"{'✓' if done_that_day else ''}</div>"
                    f"<div style='font-size:0.75rem;margin-top:4px;color:#64748b'>{day.strftime('%a')}</div>"
                    f"<div style='font-size:0.75rem;color:#94a3b8'>{day.day}</div></div>",
                    unsafe_allow_html=True,
                )

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — MANAGE HABITS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Manage Habits":
    st.header("➕ Manage Habits")
    with st.form("add_form"):
        c1,c2,c3 = st.columns(3)
        with c1: new_name = st.text_input("Habit Name")
        with c2: new_cat  = st.selectbox("Category", CATEGORIES)
        with c3: new_goal = st.slider("Goal per week", 1, 7, 5)
        if st.form_submit_button("Add Habit", use_container_width=True):
            ok, msg = add_habit(user_id, new_name, new_cat, new_goal)
            if ok: st.success(msg); st.rerun()
            else:  st.error(msg)

    st.divider()
    st.markdown("### Your Habits")
    if not habits:
        st.info("No habits yet. Add one above!")
    else:
        for h in habits:
            dates       = get_checkins_for_habit(h["id"])
            cur, best   = streak_stats(dates)
            is_expanded = st.session_state.expanded_habit == h["id"]
            hc1, hc2   = st.columns([6,1])
            with hc1:
                st.markdown(
                    f"<div style='background:#f8faff;border:1px solid #e2e8f0;border-radius:10px;"
                    f"padding:14px 18px;margin-bottom:4px'>"
                    f"<span style='font-weight:700;font-size:1rem;color:#1a1a2e'>{h['name']}</span>"
                    f"&nbsp;&nbsp;<span style='background:#e2e8f0;border-radius:6px;padding:2px 10px;"
                    f"font-size:0.8rem;color:#475569'>{h['category']}</span>"
                    f"&nbsp;&nbsp;<span style='font-size:0.85rem;color:#64748b'>"
                    f"🔥 {cur}d &nbsp;🏆 {best}d &nbsp;📅 {len(dates)} check-ins</span></div>",
                    unsafe_allow_html=True,
                )
            with hc2:
                if st.button("Hide" if is_expanded else "Edit", key=f"tog_{h['id']}"):
                    st.session_state.expanded_habit = None if is_expanded else h["id"]
                    st.rerun()
            if is_expanded:
                l, r = st.columns([3,1])
                with l:
                    with st.form(f"edit_{h['id']}"):
                        e_name = st.text_input("Name", value=h["name"])
                        e_cat  = st.selectbox("Category", CATEGORIES,
                                    index=CATEGORIES.index(h["category"]) if h["category"] in CATEGORIES else 0)
                        e_goal = st.slider("Goal per week", 1, 7, int(h["goal_per_week"]))
                        if st.form_submit_button("Save Changes", use_container_width=True):
                            update_habit(h["id"], e_name, e_cat, e_goal)
                            st.session_state.expanded_habit = None
                            st.success("Updated!"); st.rerun()
                with r:
                    st.markdown(
                        f"<div style='background:#f8faff;border:1px solid #e2e8f0;"
                        f"border-radius:10px;padding:16px'>"
                        f"<p style='margin:4px 0'><b>Total:</b> {len(dates)} check-ins</p>"
                        f"<p style='margin:4px 0'><b>Current:</b> 🔥 {cur}d</p>"
                        f"<p style='margin:4px 0'><b>Best:</b> 🏆 {best}d</p>"
                        f"<p style='margin:4px 0'><b>Goal:</b> {h['goal_per_week']}x/week</p></div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown("")
                    if st.button("🗑 Delete", key=f"del_{h['id']}", type="secondary", use_container_width=True):
                        delete_habit(h["id"]); st.session_state.expanded_habit = None; st.rerun()

    st.divider()
    st.markdown("### Log a Past Check-in")
    if not habits:
        st.info("Add a habit first.")
    else:
        with st.form("past_checkin_form"):
            sel_name = st.selectbox("Habit", [h["name"] for h in habits])
            sel_date = st.date_input("Date", max_value=date.today())
            if st.form_submit_button("Log Check-in"):
                sel_h = next(h for h in habits if h["name"] == sel_name)
                toggle_checkin(sel_h["id"], str(sel_date))
                st.success(f"Logged **{sel_name}** on {sel_date}!"); st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Analytics":
    st.header("📊 Analytics")
    if not checkins:
        st.info("No check-ins yet. Start tracking your habits!")
    else:
        df = pd.DataFrame(checkins)
        df["date"] = pd.to_datetime(df["date"])
        all_dates            = sorted(set(c["date"] for c in checkins))
        cur_streak, best_str = streak_stats(all_dates)

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("✅ Total Check-ins", len(checkins))
        c2.metric("🗂 Habits Tracked",  len(habits))
        c3.metric("🔥 Current Streak",  f"{cur_streak}d")
        c4.metric("🏆 Best Streak",      f"{best_str}d")

        st.divider()
        cl, cr = st.columns(2)
        with cl:
            st.markdown("### Completions per Habit")
            hc = df.groupby("name").size().sort_values()
            fig, ax = plt.subplots(figsize=(6, max(3, len(hc)*0.6)))
            ax.set_facecolor("#f8faff"); fig.patch.set_facecolor("#f8faff")
            colors = plt.cm.viridis([i/max(len(hc),1) for i in range(len(hc))])
            bars = ax.barh(hc.index, hc.values, color=colors)
            ax.bar_label(bars, padding=4, fontsize=9)
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False); ax.set_xlabel("Check-ins")
            plt.tight_layout(); st.pyplot(fig); plt.close()
        with cr:
            st.markdown("### Completion by Day of Week")
            df["dow"]  = df["date"].dt.day_name()
            day_order  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            dow_counts = df["dow"].value_counts().reindex(day_order, fill_value=0)
            fig2, ax2  = plt.subplots(figsize=(6,4))
            ax2.set_facecolor("#f8faff"); fig2.patch.set_facecolor("#f8faff")
            ax2.bar(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], dow_counts.values,
                    color=sns.color_palette("coolwarm",7))
            ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)
            ax2.set_ylabel("Check-ins")
            plt.tight_layout(); st.pyplot(fig2); plt.close()

        st.divider()
        st.markdown("### Weekly Completion Heatmap (last 8 weeks)")
        pivot = weekly_completion(checkins)
        if not pivot.empty:
            last8 = pivot.tail(8)
            fig3, ax3 = plt.subplots(figsize=(12, max(3, len(last8.columns)*0.5+1)))
            fig3.patch.set_facecolor("#f8faff"); ax3.set_facecolor("#f8faff")
            sns.heatmap(last8.T, annot=True, fmt="d", cmap="YlGn", linewidths=0.5, ax=ax3)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout(); st.pyplot(fig3); plt.close()

        st.divider()
        cl2, cr2 = st.columns(2)
        with cl2:
            st.markdown("### Check-ins by Category")
            cat_counts = df.groupby("category").size()
            fig4, ax4  = plt.subplots(figsize=(5,4))
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
                board.append({"Habit": h["name"], "Current 🔥": ch, "Best 🏆": bh, "Total": len(dh)})
            st.dataframe(pd.DataFrame(board).sort_values("Best 🏆", ascending=False),
                         use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4 — ML PREDICTIONS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "ML Predictions":
    st.header("🤖 ML Predictions")
    st.markdown("*Logistic Regression model trained on your personal check-in history.*")
    if not habits:
        st.info("Add habits and check in for a few days to unlock ML predictions!")
    else:
        sel_name   = st.selectbox("Choose a habit", [h["name"] for h in habits])
        days_ahead = st.slider("Days ahead to predict", 3, 14, 7)
        sel_h      = next(h for h in habits if h["name"] == sel_name)
        dates      = get_checkins_for_habit(sel_h["id"])
        cur_s, best_s = streak_stats(dates)

        c1,c2,c3 = st.columns(3)
        c1.metric("📅 Total Check-ins", len(dates))
        c2.metric("🔥 Current Streak",  f"{cur_s}d")
        c3.metric("🏆 Best Streak",     f"{best_s}d")

        st.divider()
        dow = best_day_of_week(dates)
        if any(v > 0 for v in dow.values()):
            best_day = max(dow, key=dow.get)
            st.markdown(f"📅 Your **best day** for *{sel_name}* is **{best_day}** with {dow[best_day]} check-ins.")
            fig5, ax5 = plt.subplots(figsize=(7,3))
            ax5.set_facecolor("#f8faff"); fig5.patch.set_facecolor("#f8faff")
            ax5.bar(list(dow.keys()), list(dow.values()),
                    color=["#28a745" if d == best_day else "#adb5bd" for d in dow])
            ax5.set_ylabel("Check-ins"); ax5.set_title("Completions by day of week")
            ax5.spines["top"].set_visible(False); ax5.spines["right"].set_visible(False)
            plt.tight_layout(); st.pyplot(fig5); plt.close()

        st.divider()
        st.markdown("### Predicted completion probability")
        pred_df, err = build_features(dates, days_ahead)
        if err:
            st.warning(err)
        else:
            bar_colors = ["#28a745" if p>=70 else "#fd7e14" if p>=40 else "#dc3545"
                          for p in pred_df["probability"]]
            x_labels = [date.fromisoformat(d).strftime("%b %d") for d in pred_df["date"]]
            fig6, ax6 = plt.subplots(figsize=(10,4))
            ax6.set_facecolor("#f8faff"); fig6.patch.set_facecolor("#f8faff")
            ax6.bar(x_labels, pred_df["probability"], color=bar_colors)
            ax6.axhline(70, color="#28a745", linestyle="--", alpha=0.6, linewidth=1.5)
            ax6.axhline(40, color="#fd7e14", linestyle="--", alpha=0.6, linewidth=1.5)
            ax6.legend(handles=[
                mpatches.Patch(color="#28a745", label="High (>=70%)"),
                mpatches.Patch(color="#fd7e14", label="Medium (40-69%)"),
                mpatches.Patch(color="#dc3545", label="Low (<40%)"),
            ], loc="upper right")
            ax6.set_ylabel("Probability (%)"); ax6.set_ylim(0, 110)
            ax6.spines["top"].set_visible(False); ax6.spines["right"].set_visible(False)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout(); st.pyplot(fig6); plt.close()

            def likelihood(p):
                return "High" if p>=70 else ("Medium" if p>=40 else "Low")
            disp = pred_df.copy()
            disp.columns = ["Date","Probability (%)"]
            disp["Likelihood"] = disp["Probability (%)"].apply(likelihood)
            st.dataframe(disp, use_container_width=True, hide_index=True)
            avg = pred_df["probability"].mean()
            if avg>=70:   st.success(f"Strong week ahead! Average: {avg:.1f}%")
            elif avg>=40: st.warning(f"Moderate week. Average: {avg:.1f}% — stay consistent!")
            else:         st.error(f"Challenging week predicted: {avg:.1f}% — try to build momentum!")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 5 — STEPS TRACKER
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Steps Tracker":
    st.header("👟 Steps Tracker")
    today_entry = get_steps_today(user_id)
    history_30  = get_steps_history(user_id, days=30)
    all_entries = get_steps_all(user_id)

    today_steps = today_entry["steps"] if today_entry else 0
    today_goal  = today_entry["goal"]  if today_entry else 10000
    pct_done    = min(int(today_steps / today_goal * 100), 100) if today_goal else 0
    steps_left  = max(0, today_goal - today_steps)
    total_days  = len(all_entries)
    goal_days   = sum(1 for e in all_entries if e["steps"] >= e["goal"])
    avg_steps   = int(sum(e["steps"] for e in all_entries) / total_days) if total_days else 0
    best_steps  = max((e["steps"] for e in all_entries), default=0)

    streak_count = 0
    for e in sorted(all_entries, key=lambda x: x["date"], reverse=True):
        if e["steps"] >= e["goal"]: streak_count += 1
        else: break

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("👟 Today's Steps", f"{today_steps:,}")
    c2.metric("🎯 Daily Goal",     f"{today_goal:,}")
    c3.metric("🔥 Goal Streak",    f"{streak_count}d")
    c4.metric("📅 Days Logged",    total_days)

    st.divider()
    lc, rc = st.columns([1,1])
    with lc:
        st.markdown("### Today's Progress")
        ring_color = "#28a745" if pct_done>=100 else "#3b82f6" if pct_done>=50 else "#f59e0b"
        fig = donut_chart(today_steps, today_goal, ring_color, "steps", size=3.5)
        st.pyplot(fig); plt.close()
        if pct_done >= 100: st.success("🎉 Goal reached! Amazing work today!")
        elif steps_left > 0: st.info(f"💪 {steps_left:,} more steps to reach your goal!")

    with rc:
        st.markdown("### Log Steps")
        with st.form("steps_form"):
            step_input = st.number_input("Steps taken", min_value=0, max_value=100000,
                                         value=today_steps, step=100)
            goal_input = st.number_input("Daily goal", min_value=1000, max_value=50000,
                                         value=today_goal, step=500)
            note_input = st.text_input("Note (optional)",
                                       value=today_entry["note"] if today_entry else "")
            log_date_input = st.date_input("Date", value=date.today(), max_value=date.today())
            if st.form_submit_button("Save Steps", use_container_width=True):
                log_steps(user_id, step_input, goal_input, str(log_date_input), note_input)
                st.success(f"Saved {step_input:,} steps!"); st.rerun()

        st.markdown("#### Quick Add")
        qa1,qa2,qa3,qa4 = st.columns(4)
        for col, amt in zip([qa1,qa2,qa3,qa4],[500,1000,2000,5000]):
            with col:
                if st.button(f"+{amt:,}", key=f"qs_{amt}", use_container_width=True):
                    log_steps(user_id, today_steps+amt, today_goal, str(date.today()),
                              today_entry["note"] if today_entry else "")
                    st.rerun()

    st.divider()
    st.markdown("### Last 30 Days")
    if history_30:
        df_h = pd.DataFrame(history_30)
        df_h["date_label"] = pd.to_datetime(df_h["date"]).dt.strftime("%b %d")
        bar_clrs = ["#28a745" if r["steps"]>=r["goal"] else
                    "#3b82f6" if r["steps"]>=r["goal"]*0.7 else "#f59e0b"
                    for _,r in df_h.iterrows()]
        fig_h, ax_h = plt.subplots(figsize=(12,4))
        fig_h.patch.set_facecolor("#f8faff"); ax_h.set_facecolor("#f8faff")
        bars_h = ax_h.bar(df_h["date_label"], df_h["steps"], color=bar_clrs, width=0.6)
        common_goal = int(df_h["goal"].mode()[0])
        ax_h.axhline(common_goal, color="#dc3545", linestyle="--", alpha=0.7,
                     linewidth=1.5, label=f"Goal: {common_goal:,}")
        ax_h.bar_label(bars_h, labels=[f"{int(v):,}" for v in df_h["steps"]],
                       padding=3, fontsize=7, rotation=45)
        ax_h.set_ylabel("Steps"); ax_h.legend(fontsize=9)
        ax_h.spines["top"].set_visible(False); ax_h.spines["right"].set_visible(False)
        plt.xticks(rotation=45, ha="right", fontsize=8)
        plt.tight_layout(); st.pyplot(fig_h); plt.close()

    st.divider()
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("📊 Avg Steps/Day", f"{avg_steps:,}")
    s2.metric("🏆 Best Day",       f"{best_steps:,}")
    s3.metric("🎯 Goals Reached",  f"{goal_days}d")
    s4.metric("📈 Success Rate",   f"{int(goal_days/total_days*100)}%" if total_days else "0%")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 6 — WATER TRACKER
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Water Tracker":
    st.header("💧 Water Intake Tracker")
    st.markdown("Stay hydrated! Log your daily water intake and build a hydration streak.")

    today_w   = get_water_today(user_id)
    history_w = get_water_history(user_id, days=30)
    all_w     = get_water_all(user_id)

    cur_glasses = today_w["glasses"] if today_w else 0.0
    cur_goal    = today_w["goal"]    if today_w else 8.0
    cur_unit    = today_w["unit"]    if today_w else "glasses"
    h_streak    = hydration_streak(user_id)
    total_days_w = len(all_w)
    goal_days_w  = sum(1 for e in all_w if e["glasses"] >= e["goal"])
    avg_glasses  = round(sum(e["glasses"] for e in all_w) / total_days_w, 1) if total_days_w else 0.0

    # ── Metrics ───────────────────────────────────────────────────────────────
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("💧 Today",          f"{cur_glasses:.1f} glasses")
    c2.metric("🎯 Daily Goal",      f"{cur_goal:.0f} glasses")
    c3.metric("🔥 Hydration Streak",f"{h_streak}d")
    c4.metric("📅 Days Logged",     total_days_w)

    st.divider()
    lc, rc = st.columns([1,1])

    with lc:
        st.markdown("### Today's Hydration")

        # Donut ring
        ring_color = "#28a745" if cur_glasses >= cur_goal else \
                     "#3b82f6" if cur_glasses >= cur_goal*0.6 else "#f59e0b"
        fig_w = donut_chart(round(cur_glasses,1), cur_goal, ring_color, "glasses", size=3.5)
        st.pyplot(fig_w); plt.close()

        # Visual glass grid (8 glasses shown)
        st.markdown("#### Glass by Glass")
        num_full  = int(cur_glasses)
        remainder = cur_glasses - num_full
        cols_g    = st.columns(8)
        for i in range(8):
            with cols_g[i]:
                if i < num_full:
                    icon = "🥛"
                elif i == num_full and remainder > 0:
                    icon = "🫗"
                else:
                    icon = "🫙"
                st.markdown(
                    f"<div style='text-align:center;font-size:1.5rem'>{icon}</div>"
                    f"<div style='text-align:center;font-size:0.65rem;color:#94a3b8'>{i+1}</div>",
                    unsafe_allow_html=True,
                )

        glasses_left = max(0, cur_goal - cur_glasses)
        if cur_glasses >= cur_goal:
            st.success("🎉 Daily water goal reached! Great hydration!")
        else:
            st.info(f"💧 {glasses_left:.1f} more glasses to reach your goal!")

    with rc:
        st.markdown("### Log Water")
        with st.form("water_form"):
            unit_sel = st.radio("Unit", ["glasses", "ml", "oz"],
                                index=["glasses","ml","oz"].index(cur_unit)
                                if cur_unit in ["glasses","ml","oz"] else 0,
                                horizontal=True)

            if unit_sel == "glasses":
                glass_label  = "Glasses of water"
                max_val      = 20.0
                step_val     = 0.5
                goal_default = float(cur_goal) if cur_unit == "glasses" else 8.0
                goal_max     = 20.0
            elif unit_sel == "ml":
                glass_label  = "Amount (ml)"
                max_val      = 5000.0
                step_val     = 50.0
                goal_default = float(cur_goal) if cur_unit == "ml" else 2000.0
                goal_max     = 5000.0
            else:
                glass_label  = "Amount (oz)"
                max_val      = 200.0
                step_val     = 4.0
                goal_default = float(cur_goal) if cur_unit == "oz" else 64.0
                goal_max     = 200.0

            water_input = st.number_input(
                glass_label, min_value=0.0, max_value=max_val,
                value=float(cur_glasses), step=step_val, format="%.1f"
            )
            goal_input_w = st.number_input(
                "Daily goal", min_value=1.0, max_value=goal_max,
                value=goal_default, step=step_val, format="%.1f"
            )
            note_w = st.text_input("Note (optional)",
                                   value=today_w["note"] if today_w else "")
            log_date_w = st.date_input("Date", value=date.today(), max_value=date.today())
            if st.form_submit_button("Save Water Intake", use_container_width=True):
                log_water(user_id, water_input, goal_input_w, unit_sel,
                          str(log_date_w), note_w)
                st.success(f"Saved {water_input:.1f} {unit_sel}!"); st.rerun()

        # Quick add buttons
        st.markdown("#### Quick Add (glasses)")
        qa1,qa2,qa3,qa4 = st.columns(4)
        for col, amt, lbl in zip(
            [qa1,qa2,qa3,qa4],
            [0.5,  1,  2,  3 ],
            ["+½", "+1","+2","+3"]
        ):
            with col:
                if st.button(lbl, key=f"wq_{amt}", use_container_width=True):
                    new_val = round(cur_glasses + amt, 1)
                    log_water(user_id, new_val, cur_goal, cur_unit,
                              str(date.today()), today_w["note"] if today_w else "")
                    st.rerun()

    st.divider()

    # ── 30-day bar chart ──────────────────────────────────────────────────────
    st.markdown("### Last 30 Days")
    if history_w:
        df_wh = pd.DataFrame(history_w)
        df_wh["date_label"] = pd.to_datetime(df_wh["date"]).dt.strftime("%b %d")
        wbar_clrs = ["#28a745" if r["glasses"]>=r["goal"] else
                     "#3b82f6" if r["glasses"]>=r["goal"]*0.6 else "#f59e0b"
                     for _,r in df_wh.iterrows()]
        fig_wh, ax_wh = plt.subplots(figsize=(12,4))
        fig_wh.patch.set_facecolor("#f8faff"); ax_wh.set_facecolor("#f8faff")
        bars_wh = ax_wh.bar(df_wh["date_label"], df_wh["glasses"],
                             color=wbar_clrs, width=0.6)
        common_goal_w = float(df_wh["goal"].mode()[0])
        ax_wh.axhline(common_goal_w, color="#dc3545", linestyle="--",
                      alpha=0.7, linewidth=1.5, label=f"Goal: {common_goal_w:.0f}")
        ax_wh.bar_label(bars_wh,
                        labels=[f"{v:.1f}" for v in df_wh["glasses"]],
                        padding=3, fontsize=8)
        ax_wh.set_ylabel("Glasses"); ax_wh.legend(fontsize=9)
        ax_wh.spines["top"].set_visible(False); ax_wh.spines["right"].set_visible(False)
        plt.xticks(rotation=45, ha="right", fontsize=8)
        plt.tight_layout(); st.pyplot(fig_wh); plt.close()
    else:
        st.info("No history yet. Start logging today!")

    # ── 7-day streak row ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 7-Day Hydration Streak")
    done_dates_w = {e["date"] for e in all_w if e["glasses"] >= e["goal"]}
    day7_cols    = st.columns(7)
    for i, col in enumerate(day7_cols):
        d     = date.today() - timedelta(days=6 - i)
        hit   = str(d) in done_dates_w
        bg    = "#3b82f6" if hit else "#e9ecef"
        color = "#ffffff" if hit else "#6c757d"
        with col:
            st.markdown(
                f"<div style='text-align:center'>"
                f"<div style='width:36px;height:36px;border-radius:50%;background:{bg};"
                f"margin:0 auto;display:flex;align-items:center;justify-content:center;"
                f"font-size:1rem;color:{color};font-weight:700'>{'💧' if hit else ''}</div>"
                f"<div style='font-size:0.72rem;margin-top:4px;color:#64748b'>{d.strftime('%a')}</div>"
                f"<div style='font-size:0.72rem;color:#94a3b8'>{d.day}</div></div>",
                unsafe_allow_html=True,
            )

    # ── All-time stats ────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### All-time Stats")
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("📊 Avg/Day",       f"{avg_glasses:.1f} glasses")
    s2.metric("🎯 Goals Reached", f"{goal_days_w}d")
    s3.metric("📅 Total Logged",  f"{total_days_w}d")
    s4.metric("📈 Success Rate",  f"{int(goal_days_w/total_days_w*100)}%" if total_days_w else "0%")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 7 — SLEEP TRACKER
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Sleep Tracker":
    st.header("😴 Sleep Tracker")
    st.markdown("Track your sleep and build healthy bedtime habits. Optimal: **7–9 hours**.")

    today_s   = get_sleep_today(user_id)
    history_s = get_sleep_history(user_id, days=30)
    all_s     = get_sleep_all(user_id)

    cur_hours   = today_s["hours_slept"] if today_s else 0.0
    cur_quality = today_s["quality"]     if today_s else 3
    s_streak    = sleep_streak(user_id)
    total_days_s = len(all_s)
    avg_hours    = round(sum(e["hours_slept"] for e in all_s)/total_days_s, 1) if total_days_s else 0.0
    best_hours   = max((e["hours_slept"] for e in all_s), default=0.0)
    goal_days_s  = sum(1 for e in all_s if 7 <= e["hours_slept"] <= 9)

    QUALITY_LABELS = {1:"😞 Poor",2:"😐 Fair",3:"🙂 Good",4:"😀 Great",5:"🤩 Amazing"}

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("😴 Last Night",    f"{cur_hours:.1f} hrs")
    c2.metric("🎯 Optimal Range", "7–9 hrs")
    c3.metric("🔥 Good Sleep Streak", f"{s_streak}d")
    c4.metric("📊 Avg Sleep",     f"{avg_hours:.1f} hrs")

    st.divider()
    lc, rc = st.columns([1,1])

    with lc:
        st.markdown("### Last Night")

        # Donut ring (goal = 8 hrs optimal)
        ring_color = "#28a745" if 7<=cur_hours<=9 else \
                     "#f59e0b" if cur_hours>=6 else "#dc3545"
        fig_s = donut_chart(round(cur_hours,1), 9, ring_color, "hrs slept",
                            unit="h", size=3.5)
        st.pyplot(fig_s); plt.close()

        # Status message
        if cur_hours == 0:
            st.info("No sleep logged yet for today. Log it on the right!")
        elif cur_hours < 6:
            st.error(f"😞 Only {cur_hours:.1f}h — you need more rest!")
        elif cur_hours < 7:
            st.warning(f"🟡 {cur_hours:.1f}h — a bit under the optimal range.")
        elif cur_hours <= 9:
            st.success(f"✅ {cur_hours:.1f}h — perfect! You're in the optimal range.")
        else:
            st.warning(f"🟡 {cur_hours:.1f}h — slightly over. Oversleeping can cause fatigue.")

        # Quality display
        if today_s:
            q_label = QUALITY_LABELS.get(cur_quality, "")
            st.markdown(
                f"<div style='text-align:center;margin-top:8px;font-size:1.1rem'>"
                f"Sleep quality: <b>{q_label}</b></div>",
                unsafe_allow_html=True,
            )

    with rc:
        st.markdown("### Log Sleep")
        with st.form("sleep_form"):
            log_date_s = st.date_input("Sleep date (night of)", value=date.today(),
                                        max_value=date.today())

            default_bed  = today_s["bedtime"]   if today_s else "23:00"
            default_wake = today_s["wake_time"]  if today_s else "07:00"

            bedtime_str  = st.text_input("Bedtime (HH:MM, 24h)", value=default_bed,
                                          placeholder="23:00")
            waketime_str = st.text_input("Wake time (HH:MM, 24h)", value=default_wake,
                                          placeholder="07:00")
            quality_sel  = st.select_slider(
                "Sleep quality",
                options=[1,2,3,4,5],
                value=cur_quality,
                format_func=lambda x: QUALITY_LABELS[x],
            )
            note_s = st.text_input("Note (optional)",
                                   value=today_s["note"] if today_s else "")

            if st.form_submit_button("Save Sleep", use_container_width=True):
                try:
                    bt  = datetime.strptime(bedtime_str.strip(),  "%H:%M").time()
                    wt  = datetime.strptime(waketime_str.strip(), "%H:%M").time()
                    bed_dt  = datetime.combine(log_date_s, bt)
                    wake_dt = datetime.combine(log_date_s, wt)
                    if wake_dt <= bed_dt:          # woke up next day
                        wake_dt += timedelta(days=1)
                    hours = round((wake_dt - bed_dt).seconds / 3600, 2)
                    log_sleep(user_id, bedtime_str.strip(), waketime_str.strip(),
                              hours, quality_sel, str(log_date_s), note_s)
                    st.success(f"Saved! You slept {hours:.1f} hours."); st.rerun()
                except ValueError:
                    st.error("Invalid time format. Please use HH:MM (e.g. 23:00)")

    st.divider()

    # ── 30-day trend chart ────────────────────────────────────────────────────
    st.markdown("### 30-Day Sleep Trend")
    if history_s:
        df_sh = pd.DataFrame(history_s)
        df_sh["date_label"] = pd.to_datetime(df_sh["date"]).dt.strftime("%b %d")
        sbar_clrs = ["#28a745" if 7<=r["hours_slept"]<=9 else
                     "#f59e0b" if r["hours_slept"]>=6 else "#dc3545"
                     for _,r in df_sh.iterrows()]
        fig_sh, ax_sh = plt.subplots(figsize=(12,4))
        fig_sh.patch.set_facecolor("#f8faff"); ax_sh.set_facecolor("#f8faff")
        ax_sh.bar(df_sh["date_label"], df_sh["hours_slept"],
                  color=sbar_clrs, width=0.6)
        ax_sh.axhspan(7, 9, alpha=0.10, color="#28a745", label="Optimal (7–9h)")
        ax_sh.axhline(7, color="#28a745", linestyle="--", alpha=0.5, linewidth=1)
        ax_sh.axhline(9, color="#28a745", linestyle="--", alpha=0.5, linewidth=1)
        ax_sh.set_ylabel("Hours Slept"); ax_sh.set_ylim(0, 13)
        ax_sh.legend(fontsize=9)
        ax_sh.spines["top"].set_visible(False); ax_sh.spines["right"].set_visible(False)
        plt.xticks(rotation=45, ha="right", fontsize=8)
        plt.tight_layout(); st.pyplot(fig_sh); plt.close()

        lc2,rc2 = st.columns(2)
        lc2.markdown("🟢 **Green** — Optimal (7–9h)")
        lc2.markdown("🟡 **Yellow** — Acceptable (6–7h)")
        rc2.markdown("🔴 **Red** — Poor (<6h or logged as 0)")

        # Quality trend
        st.divider()
        st.markdown("### Sleep Quality Trend")
        fig_q, ax_q = plt.subplots(figsize=(12,3))
        fig_q.patch.set_facecolor("#f8faff"); ax_q.set_facecolor("#f8faff")
        q_colors = ["#dc3545","#fd7e14","#ffc107","#28a745","#0d6efd"]
        ax_q.scatter(df_sh["date_label"], df_sh["quality"],
                     c=[q_colors[int(q)-1] for q in df_sh["quality"]], s=80, zorder=3)
        ax_q.plot(df_sh["date_label"], df_sh["quality"],
                  color="#94a3b8", linewidth=1, zorder=2)
        ax_q.set_yticks([1,2,3,4,5])
        ax_q.set_yticklabels(["Poor","Fair","Good","Great","Amazing"])
        ax_q.set_ylim(0.5, 5.5)
        ax_q.spines["top"].set_visible(False); ax_q.spines["right"].set_visible(False)
        plt.xticks(rotation=45, ha="right", fontsize=8)
        plt.tight_layout(); st.pyplot(fig_q); plt.close()
    else:
        st.info("No sleep history yet. Start logging tonight!")

    # ── Stats ─────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### All-time Stats")
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("📊 Avg Sleep",       f"{avg_hours:.1f} hrs")
    s2.metric("🏆 Best Night",       f"{best_hours:.1f} hrs")
    s3.metric("✅ Optimal Nights",   f"{goal_days_s}d")
    s4.metric("📈 Success Rate",     f"{int(goal_days_s/total_days_s*100)}%" if total_days_s else "0%")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 8 — WEIGHT TRACKER
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Weight Tracker":
    st.header("⚖️ Weight Tracker")
    st.markdown("Log your weight, set a goal, and track your progress over time.")

    today_wt    = get_weight_today(user_id)
    latest_wt   = get_latest_weight(user_id)
    history_wt  = get_weight_history(user_id, days=90)
    all_wt      = get_weight_all(user_id)

    # Determine unit preference from last entry
    pref_unit   = latest_wt["unit"] if latest_wt else "kg"
    cur_weight  = latest_wt["weight_kg"] if latest_wt else 70.0
    cur_goal_kg = latest_wt["goal_kg"]   if latest_wt and latest_wt["goal_kg"] else None

    def kg_to_lbs(kg): return round(kg * 2.20462, 1)
    def lbs_to_kg(lbs): return round(lbs / 2.20462, 2)
    def display_w(kg, unit): return f"{kg_to_lbs(kg):.1f}" if unit=="lbs" else f"{kg:.1f}"

    total_days_wt = len(all_wt)
    change_kg     = 0.0
    if len(all_wt) >= 2:
        change_kg = round(all_wt[-1]["weight_kg"] - all_wt[0]["weight_kg"], 1)

    # ── Metrics ───────────────────────────────────────────────────────────────
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("⚖️ Current Weight",
              f"{display_w(cur_weight, pref_unit)} {pref_unit}")
    c2.metric("🎯 Goal Weight",
              f"{display_w(cur_goal_kg, pref_unit)} {pref_unit}"
              if cur_goal_kg else "Not set")
    diff_label = f"{'↓' if change_kg<0 else '↑'} {abs(change_kg):.1f} kg total"
    c3.metric("📉 Change", diff_label if total_days_wt >= 2 else "—")
    c4.metric("📅 Days Logged", total_days_wt)

    st.divider()
    lc, rc = st.columns([1,1])

    with lc:
        st.markdown("### Progress to Goal")
        if cur_goal_kg and latest_wt:
            start_wt    = all_wt[0]["weight_kg"] if all_wt else cur_weight
            total_diff  = abs(start_wt - cur_goal_kg)
            done_diff   = abs(cur_weight - start_wt)
            pct_progress = min(int(done_diff/total_diff*100), 100) if total_diff > 0 else 0
            direction   = "lose" if cur_goal_kg < start_wt else "gain"
            remaining   = abs(cur_weight - cur_goal_kg)
            ring_color  = "#28a745" if pct_progress >= 80 else \
                          "#3b82f6" if pct_progress >= 40 else "#f59e0b"
            w_val = kg_to_lbs(cur_weight) if pref_unit=="lbs" else cur_weight
            fig_wt = donut_chart(pct_progress, 100, ring_color,
                                 "goal progress", unit="%", size=3.5)
            st.pyplot(fig_wt); plt.close()
            rem_disp = f"{kg_to_lbs(remaining):.1f} lbs" if pref_unit=="lbs" \
                       else f"{remaining:.1f} kg"
            if pct_progress >= 100:
                st.success("🎉 Goal reached! Incredible work!")
            else:
                st.info(f"💪 {rem_disp} left to {direction}.")
        else:
            st.markdown(
                "<div style='background:#f8faff;border:1px solid #e2e8f0;border-radius:12px;"
                "padding:40px;text-align:center;color:#64748b'>"
                "<div style='font-size:3rem'>⚖️</div>"
                "<p>Set a goal weight to see progress here</p></div>",
                unsafe_allow_html=True,
            )

        # ── BMI Calculator ────────────────────────────────────────────────────
        st.markdown("### BMI Calculator")
        bmi_col1, bmi_col2 = st.columns(2)
        with bmi_col1:
            height_cm = st.number_input("Height (cm)", min_value=100, max_value=250,
                                         value=170, step=1)
        with bmi_col2:
            bmi_weight = st.number_input(
                f"Weight ({pref_unit})",
                min_value=1.0, max_value=300.0,
                value=float(kg_to_lbs(cur_weight)) if pref_unit=="lbs" else float(cur_weight),
                step=0.1, format="%.1f"
            )

        bmi_kg  = lbs_to_kg(bmi_weight) if pref_unit=="lbs" else bmi_weight
        h_m     = height_cm / 100
        bmi_val = round(bmi_kg / (h_m ** 2), 1)

        if bmi_val < 18.5:
            bmi_cat, bmi_col = "Underweight", "#3b82f6"
        elif bmi_val < 25:
            bmi_cat, bmi_col = "Normal weight", "#28a745"
        elif bmi_val < 30:
            bmi_cat, bmi_col = "Overweight", "#f59e0b"
        else:
            bmi_cat, bmi_col = "Obese", "#dc3545"

        st.markdown(
            f"<div style='background:{bmi_col}18;border:2px solid {bmi_col};"
            f"border-radius:12px;padding:16px;text-align:center;margin-top:8px'>"
            f"<div style='font-size:2.2rem;font-weight:800;color:{bmi_col}'>{bmi_val}</div>"
            f"<div style='font-size:1rem;font-weight:600;color:{bmi_col}'>{bmi_cat}</div>"
            f"<div style='font-size:0.8rem;color:#64748b;margin-top:4px'>"
            f"Underweight &lt;18.5 | Normal 18.5–24.9 | Overweight 25–29.9 | Obese ≥30</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with rc:
        st.markdown("### Log Weight")
        with st.form("weight_form"):
            unit_sel_wt = st.radio("Unit", ["kg","lbs"],
                                   index=0 if pref_unit=="kg" else 1,
                                   horizontal=True)
            cur_display = kg_to_lbs(cur_weight) if unit_sel_wt=="lbs" else cur_weight
            weight_input = st.number_input(
                f"Weight ({unit_sel_wt})",
                min_value=1.0, max_value=500.0,
                value=float(round(cur_display,1)),
                step=0.1, format="%.1f"
            )
            goal_display = (kg_to_lbs(cur_goal_kg) if unit_sel_wt=="lbs" else cur_goal_kg) \
                           if cur_goal_kg else (60.0 if unit_sel_wt=="kg" else 132.0)
            goal_input_wt = st.number_input(
                f"Goal weight ({unit_sel_wt})",
                min_value=1.0, max_value=500.0,
                value=float(round(goal_display,1)),
                step=0.1, format="%.1f"
            )
            note_wt    = st.text_input("Note (optional)",
                                       value=today_wt["note"] if today_wt else "")
            log_date_wt = st.date_input("Date", value=date.today(), max_value=date.today())

            if st.form_submit_button("Save Weight", use_container_width=True):
                w_kg  = lbs_to_kg(weight_input) if unit_sel_wt=="lbs" else weight_input
                g_kg  = lbs_to_kg(goal_input_wt) if unit_sel_wt=="lbs" else goal_input_wt
                log_weight(user_id, w_kg, g_kg, unit_sel_wt, str(log_date_wt), note_wt)
                st.success(f"Saved {weight_input:.1f} {unit_sel_wt}!"); st.rerun()

    st.divider()

    # ── Progress line chart ───────────────────────────────────────────────────
    st.markdown("### Weight Progress (last 90 days)")
    if len(history_wt) >= 2:
        df_wth = pd.DataFrame(history_wt)
        df_wth["dt"] = pd.to_datetime(df_wth["date"])
        if pref_unit == "lbs":
            df_wth["display_w"] = df_wth["weight_kg"].apply(kg_to_lbs)
            y_label = "Weight (lbs)"
        else:
            df_wth["display_w"] = df_wth["weight_kg"]
            y_label = "Weight (kg)"

        fig_wth, ax_wth = plt.subplots(figsize=(12,4))
        fig_wth.patch.set_facecolor("#f8faff"); ax_wth.set_facecolor("#f8faff")

        ax_wth.plot(df_wth["dt"], df_wth["display_w"],
                    color="#3b82f6", linewidth=2.5, marker="o",
                    markersize=4, label="Weight", zorder=3)
        ax_wth.fill_between(df_wth["dt"], df_wth["display_w"],
                             alpha=0.10, color="#3b82f6")

        # Goal line
        if cur_goal_kg:
            goal_display_line = kg_to_lbs(cur_goal_kg) if pref_unit=="lbs" else cur_goal_kg
            ax_wth.axhline(goal_display_line, color="#28a745", linestyle="--",
                           alpha=0.7, linewidth=1.5,
                           label=f"Goal: {goal_display_line:.1f} {pref_unit}")

        # Trend line
        if len(df_wth) >= 3:
            import numpy as np
            z   = np.polyfit(range(len(df_wth)), df_wth["display_w"], 1)
            p   = np.poly1d(z)
            ax_wth.plot(df_wth["dt"], p(range(len(df_wth))),
                        color="#94a3b8", linestyle=":", linewidth=1.5, label="Trend")

        ax_wth.set_ylabel(y_label)
        ax_wth.legend(fontsize=9)
        ax_wth.spines["top"].set_visible(False); ax_wth.spines["right"].set_visible(False)
        plt.xticks(rotation=30, ha="right", fontsize=8)
        plt.tight_layout(); st.pyplot(fig_wth); plt.close()
    elif len(history_wt) == 1:
        st.info("Log at least 2 entries to see a trend chart.")
    else:
        st.info("No weight history yet. Start logging today!")

    # ── History log ───────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### History Log")
    if all_wt:
        df_wl = pd.DataFrame(all_wt[::-1])
        if pref_unit == "lbs":
            df_wl["Weight"] = df_wl["weight_kg"].apply(lambda x: f"{kg_to_lbs(x):.1f} lbs")
            df_wl["Goal"]   = df_wl["goal_kg"].apply(
                lambda x: f"{kg_to_lbs(x):.1f} lbs" if x else "—")
        else:
            df_wl["Weight"] = df_wl["weight_kg"].apply(lambda x: f"{x:.1f} kg")
            df_wl["Goal"]   = df_wl["goal_kg"].apply(
                lambda x: f"{x:.1f} kg" if x else "—")
        st.dataframe(
            df_wl[["date","Weight","Goal","note"]].rename(
                columns={"date":"Date","note":"Note"}),
            use_container_width=True, hide_index=True
        )

        with st.expander("🗑 Delete an entry"):
            del_date_wt = st.date_input("Select date to delete",
                                         max_value=date.today(), key="del_wt_date")
            if st.button("Delete Entry", type="secondary", key="del_wt_btn"):
                delete_weight_entry(user_id, str(del_date_wt))
                st.success(f"Deleted entry for {del_date_wt}"); st.rerun()
    else:
        st.info("No entries yet.")