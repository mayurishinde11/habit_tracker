import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from datetime import date, timedelta

from database import (
    init_db,
    add_habit,
    get_habits,
    delete_habit,
    update_habit,
    toggle_checkin,
    is_done_today,
    get_all_checkins,
    get_checkins_for_habit,
)
from auth import (
    init_session,
    is_logged_in,
    get_current_user,
    logout,
    show_login_page,
    show_register_page,
)
from ml import build_features, streak_stats, weekly_completion, best_day_of_week

# ── Init ──────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="HabitAI", page_icon="🔥", layout="wide")

init_db()
init_session()

if not is_logged_in():
    if st.session_state.auth_page == "register":
        show_register_page()
    else:
        show_login_page()
    st.stop()

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

*, h1, h2, h3, h4, h5, h6, p, div, span, label, button, input, select, textarea {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%) !important;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: #e2e8f0 !important;
}

.metric-card {
    background: #f8faff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}

.habit-done {
    background: linear-gradient(135deg, #d4edda, #c3e6cb);
    border-left: 4px solid #28a745;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0;
}

.habit-pending {
    background: #fff;
    border-left: 4px solid #6c757d;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0;
    border: 1px solid #e9ecef;
}

.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: transform 0.15s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
}

.logout-btn > button {
    background-color: #dc3545 !important;
    color: white !important;
    border: none !important;
}

.auth-card {
    background: white;
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

CATEGORIES = ["Health", "Fitness", "Learning", "Mindfulness", "Work", "Social", "Other"]

user = get_current_user()
user_id = user["id"]
habits = get_habits(user_id)
checkins = get_all_checkins(user_id)

with st.sidebar:
    st.markdown("## 🔥 HabitAI")
    st.markdown(f"**👤 {user['username']}**")
    st.markdown(f"<small style='color:#94a3b8'>📧 {user['email']}</small>", unsafe_allow_html=True)
    st.divider()

    page = st.radio(
        "Navigation",
        ["📋 Today", "➕ Manage Habits", "📊 Analytics", "🤖 ML Predictions"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown(f"**🗂 Habits:** {len(habits)}")
    st.markdown(f"**✅ Total Check-ins:** {len(checkins)}")
    st.divider()

    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Page: Today ───────────────────────────────────────────────────────────────

if page == "📋 Today":
    st.header(f"📋 Today — {date.today().strftime('%A, %d %B %Y')}")

    if not habits:
        st.info("No habits yet. Go to **Manage Habits** to add your first one!")
    else:
        done_count = sum(1 for h in habits if is_done_today(h["id"]))
        total = len(habits)
        pct = int(done_count / total * 100) if total else 0
        total_checkins = len(checkins)

        all_dates = sorted(set(c["date"] for c in checkins))
        _, best_streak = streak_stats(all_dates)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("✅ Done Today", f"{done_count}/{total}")
        with c2:
            st.metric("📈 Completion", f"{pct}%")
        with c3:
            st.metric("🔢 Total Check-ins", total_checkins)
        with c4:
            st.metric("🏆 Best Streak", f"{best_streak}d")

        st.progress(pct / 100, text=f"Today's progress: {pct}%")
        st.markdown("### Check off your habits")

        for h in habits:
            done = is_done_today(h["id"])
            dates = get_checkins_for_habit(h["id"])
            cur, _ = streak_stats(dates)
            badge = f"🔥 {cur}d streak" if cur > 0 else "Start today!"
            css_class = "habit-done" if done else "habit-pending"

            col0, col1, col2 = st.columns([4, 2, 1])
            with col0:
                st.markdown(
                    f'<div class="{css_class}">'
                    f'<strong>{h["name"]}</strong> &nbsp;'
                    f'<span style="color:#64748b;font-size:0.85rem">{h["category"]}</span><br>'
                    f'<small>{badge}</small>'
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
            day = date.today() - timedelta(days=6 - i)
            day_str = str(day)
            done_that_day = any(c["date"] == day_str for c in checkins)
            emoji = "🟩" if done_that_day else "⬜"
            with col:
                st.markdown(
                    f"<div style='text-align:center'>{emoji}<br>"
                    f"<small>{day.strftime('%a')}</small><br>"
                    f"<small>{day.day}</small></div>",
                    unsafe_allow_html=True,
                )

# ── Page: Manage Habits ───────────────────────────────────────────────────────

elif page == "➕ Manage Habits":
    st.header("Manage Habits")

    # ── Add New Habit card ────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="background:#f8faff;border:1px solid #e2e8f0;border-radius:12px;
                    padding:20px 24px 4px 24px;margin-bottom:16px;">
            <p style="font-weight:700;font-size:1.05rem;margin-bottom:12px;color:#1a1a2e;">
                Add New Habit
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("add_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_name = st.text_input("Habit Name")
        with c2:
            new_cat = st.selectbox("Category", CATEGORIES)
        with c3:
            new_goal = st.slider("Goal per week", 1, 7, 5)
        submitted = st.form_submit_button("Add Habit", use_container_width=True)
        if submitted:
            ok, msg = add_habit(user_id, new_name, new_cat, new_goal)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.divider()
    st.markdown("### Your Habits")

    if not habits:
        st.info("No habits yet. Add one above!")
    else:
        # Track which habit card is expanded via session state
        if "expanded_habit" not in st.session_state:
            st.session_state.expanded_habit = None

        for h in habits:
            dates = get_checkins_for_habit(h["id"])
            cur, best = streak_stats(dates)
            total_h = len(dates)
            is_expanded = st.session_state.expanded_habit == h["id"]

            # Card header row
            hcol1, hcol2 = st.columns([6, 1])
            with hcol1:
                st.markdown(
                    f"""
                    <div style="background:#f8faff;border:1px solid #e2e8f0;
                                border-radius:10px 10px {'0 0' if is_expanded else '10px 10px'};
                                padding:14px 18px;margin-bottom:{'0' if is_expanded else '8px'};">
                        <span style="font-weight:700;font-size:1rem;color:#1a1a2e;">{h['name']}</span>
                        &nbsp;&nbsp;
                        <span style="background:#e2e8f0;border-radius:6px;padding:2px 10px;
                                     font-size:0.8rem;color:#475569;">{h['category']}</span>
                        &nbsp;&nbsp;
                        <span style="font-size:0.85rem;color:#64748b;">
                            🔥 {cur}d streak &nbsp; 🏆 {best}d best &nbsp; 📅 {total_h} check-ins
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with hcol2:
                toggle_label = "Hide" if is_expanded else "Edit"
                if st.button(toggle_label, key=f"toggle_expand_{h['id']}"):
                    st.session_state.expanded_habit = None if is_expanded else h["id"]
                    st.rerun()

            # Expanded edit panel
            if is_expanded:
                with st.container():
                    st.markdown(
                        """<div style="background:#ffffff;border:1px solid #e2e8f0;
                                       border-top:none;border-radius:0 0 10px 10px;
                                       padding:20px 18px;margin-bottom:8px;">
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    left, right = st.columns([3, 1])
                    with left:
                        with st.form(f"edit_{h['id']}"):
                            e_name = st.text_input("Name", value=h["name"])
                            e_cat = st.selectbox(
                                "Category",
                                CATEGORIES,
                                index=CATEGORIES.index(h["category"])
                                if h["category"] in CATEGORIES
                                else 0,
                            )
                            e_goal = st.slider("Goal per week", 1, 7, int(h["goal_per_week"]))
                            if st.form_submit_button("Save Changes", use_container_width=True):
                                update_habit(h["id"], e_name, e_cat, e_goal)
                                st.session_state.expanded_habit = None
                                st.success("Updated!")
                                st.rerun()

                    with right:
                        st.markdown(
                            f"""
                            <div style="background:#f8faff;border:1px solid #e2e8f0;
                                        border-radius:10px;padding:16px;">
                                <p style="margin:4px 0"><strong>Total:</strong> {total_h} check-ins</p>
                                <p style="margin:4px 0"><strong>Current:</strong> 🔥 {cur}d</p>
                                <p style="margin:4px 0"><strong>Best:</strong> 🏆 {best}d</p>
                                <p style="margin:4px 0"><strong>Goal:</strong> {h['goal_per_week']}x/week</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.markdown("")
                        if st.button("Delete Habit", key=f"del_{h['id']}", type="secondary", use_container_width=True):
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
            sel_name = st.selectbox("Habit", habit_names)
            sel_date = st.date_input("Date", max_value=date.today())
            if st.form_submit_button("Log Check-in"):
                sel_habit = next(h for h in habits if h["name"] == sel_name)
                toggle_checkin(sel_habit["id"], str(sel_date))
                st.success(f"Logged check-in for **{sel_name}** on {sel_date}!")
                st.rerun()

# ── Page: Analytics ───────────────────────────────────────────────────────────

elif page == "📊 Analytics":
    st.header("📊 Analytics")

    if not checkins:
        st.info("No check-ins yet. Start tracking your habits!")
    else:
        df = pd.DataFrame(checkins)
        df["date"] = pd.to_datetime(df["date"])

        all_dates = sorted(set(c["date"] for c in checkins))
        cur_streak, best_streak = streak_stats(all_dates)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("✅ Total Check-ins", len(checkins))
        with c2:
            st.metric("🗂 Habits Tracked", len(habits))
        with c3:
            st.metric("🔥 Current Streak", f"{cur_streak}d")
        with c4:
            st.metric("🏆 Best Streak", f"{best_streak}d")

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### Completions per Habit")
            habit_counts = df.groupby("name").size().sort_values()
            fig, ax = plt.subplots(figsize=(6, max(3, len(habit_counts) * 0.6)))
            ax.set_facecolor("#f8faff")
            fig.patch.set_facecolor("#f8faff")
            colors = plt.cm.viridis([i / len(habit_counts) for i in range(len(habit_counts))])
            bars = ax.barh(habit_counts.index, habit_counts.values, color=colors)
            ax.bar_label(bars, padding=4, fontsize=9)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False)
            ax.set_xlabel("Check-ins")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

        with col_right:
            st.markdown("### Completion by Day of Week")
            df["dow"] = df["date"].dt.day_name()
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dow_counts = df["dow"].value_counts().reindex(day_order, fill_value=0)
            short_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.set_facecolor("#f8faff")
            fig2.patch.set_facecolor("#f8faff")
            palette = sns.color_palette("coolwarm", 7)
            ax2.bar(short_labels, dow_counts.values, color=palette)
            ax2.spines["top"].set_visible(False)
            ax2.spines["right"].set_visible(False)
            ax2.set_ylabel("Check-ins")
            plt.tight_layout()
            st.pyplot(fig2)
            plt.close()

        st.divider()
        st.markdown("### Weekly Completion Heatmap (last 8 weeks)")
        pivot = weekly_completion(checkins)
        if not pivot.empty:
            last8 = pivot.tail(8)
            fig3, ax3 = plt.subplots(
                figsize=(12, max(3, len(last8.columns) * 0.5 + 1))
            )
            fig3.patch.set_facecolor("#f8faff")
            ax3.set_facecolor("#f8faff")
            sns.heatmap(
                last8.T,
                annot=True,
                fmt="d",
                cmap="YlGn",
                linewidths=0.5,
                ax=ax3,
            )
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            st.pyplot(fig3)
            plt.close()

        st.divider()
        col4_l, col4_r = st.columns(2)

        with col4_l:
            st.markdown("### Check-ins by Category")
            cat_counts = df.groupby("category").size()
            fig4, ax4 = plt.subplots(figsize=(5, 4))
            fig4.patch.set_facecolor("#f8faff")
            palette_set2 = sns.color_palette("Set2", len(cat_counts))
            ax4.pie(
                cat_counts.values,
                labels=cat_counts.index,
                colors=palette_set2,
                autopct="%1.0f%%",
                startangle=90,
            )
            plt.tight_layout()
            st.pyplot(fig4)
            plt.close()

        with col4_r:
            st.markdown("### Streak Leaderboard")
            leaderboard = []
            for h in habits:
                dates_h = get_checkins_for_habit(h["id"])
                cur_h, best_h = streak_stats(dates_h)
                leaderboard.append({
                    "Habit": h["name"],
                    "Current 🔥": cur_h,
                    "Best 🏆": best_h,
                    "Total": len(dates_h),
                })
            ldf = pd.DataFrame(leaderboard).sort_values("Best 🏆", ascending=False)
            st.dataframe(ldf, use_container_width=True, hide_index=True)

# ── Page: ML Predictions ──────────────────────────────────────────────────────

elif page == "🤖 ML Predictions":
    st.header("🤖 ML Predictions")
    st.markdown("*Logistic Regression model trained on your personal check-in history.*")

    if not habits:
        st.info("Add some habits and check them in for a few days to unlock ML predictions!")
    else:
        habit_names = [h["name"] for h in habits]
        sel_name = st.selectbox("Choose a habit", habit_names)
        days_ahead = st.slider("Days ahead to predict", 3, 14, 7)

        sel_habit = next(h for h in habits if h["name"] == sel_name)
        habit_id = sel_habit["id"]
        dates = get_checkins_for_habit(habit_id)
        cur_s, best_s = streak_stats(dates)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("📅 Total Check-ins", len(dates))
        with c2:
            st.metric("🔥 Current Streak", f"{cur_s}d")
        with c3:
            st.metric("🏆 Best Streak", f"{best_s}d")

        st.divider()

        dow = best_day_of_week(dates)
        if any(v > 0 for v in dow.values()):
            best_day = max(dow, key=dow.get)
            st.markdown(f"📅 Your **best day** for *{sel_name}* is **{best_day}** with {dow[best_day]} check-ins.")

            fig5, ax5 = plt.subplots(figsize=(7, 3))
            ax5.set_facecolor("#f8faff")
            fig5.patch.set_facecolor("#f8faff")
            bar_colors = ["#28a745" if d == best_day else "#adb5bd" for d in dow.keys()]
            ax5.bar(list(dow.keys()), list(dow.values()), color=bar_colors)
            ax5.set_ylabel("Check-ins")
            ax5.set_title("Completions by day of week")
            ax5.spines["top"].set_visible(False)
            ax5.spines["right"].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig5)
            plt.close()

        st.divider()
        st.markdown("### Predicted completion probability")

        pred_df, err = build_features(dates, days_ahead)

        if err:
            st.warning(err)
        else:
            # Bar chart
            bar_colors_pred = []
            for p in pred_df["probability"]:
                if p >= 70:
                    bar_colors_pred.append("#28a745")
                elif p >= 40:
                    bar_colors_pred.append("#fd7e14")
                else:
                    bar_colors_pred.append("#dc3545")

            x_labels = [
                date.fromisoformat(d).strftime("%b %d")
                for d in pred_df["date"]
            ]

            fig6, ax6 = plt.subplots(figsize=(10, 4))
            ax6.set_facecolor("#f8faff")
            fig6.patch.set_facecolor("#f8faff")
            ax6.bar(x_labels, pred_df["probability"], color=bar_colors_pred)
            ax6.axhline(70, color="#28a745", linestyle="--", alpha=0.6, linewidth=1.5)
            ax6.axhline(40, color="#fd7e14", linestyle="--", alpha=0.6, linewidth=1.5)

            patch_high = mpatches.Patch(color="#28a745", label="High (≥70%)")
            patch_med = mpatches.Patch(color="#fd7e14", label="Medium (40–69%)")
            patch_low = mpatches.Patch(color="#dc3545", label="Low (<40%)")
            ax6.legend(handles=[patch_high, patch_med, patch_low], loc="upper right")

            ax6.set_ylabel("Probability (%)")
            ax6.set_ylim(0, 110)
            ax6.spines["top"].set_visible(False)
            ax6.spines["right"].set_visible(False)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            st.pyplot(fig6)
            plt.close()

            # Table
            def likelihood(p):
                if p >= 70:
                    return "🟢 High"
                elif p >= 40:
                    return "🟡 Medium"
                return "🔴 Low"

            display_df = pred_df.copy()
            display_df.columns = ["Date", "Probability (%)"]
            display_df["Likelihood"] = display_df["Probability (%)"].apply(likelihood)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            avg = pred_df["probability"].mean()
            if avg >= 70:
                st.success(f"✅ Strong week ahead! Average: {avg:.1f}%")
            elif avg >= 40:
                st.warning(f"⚠️ Moderate week. Average: {avg:.1f}% — stay consistent!")
            else:
                st.error(f"🔴 Challenging week predicted: {avg:.1f}% — try to build momentum!")