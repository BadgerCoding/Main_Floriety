"""
Floriety Admin Dashboard — Streamlit
Run: streamlit run admin.py
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

try:
    import altair as alt
except ImportError:
    alt = None

API_URL = "http://localhost:5000"

st.set_page_config(
    page_title="Floriety Admin",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS matching Floriety dark/green theme ───────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@700;800&display=swap');

    .stApp {
        background-color: #0D0F0D;
        color: #FAF9F5;
    }

    section[data-testid="stSidebar"] {
        background-color: #121412 !important;
        border-right: 1px solid #242624;
    }

    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #5DFF3C !important;
    }

    h1, h2, h3, h4 { color: #FAF9F5 !important; font-family: 'Manrope', sans-serif !important; }
    p, span, label, div { font-family: 'Inter', sans-serif !important; }

    .metric-card {
        background: #1A1C1A;
        border: 1px solid #2a2d2a;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        transition: border-color 0.2s;
    }
    .metric-card:hover { border-color: #5DFF3C; }
    .metric-value {
        font-size: 42px;
        font-weight: 800;
        color: #5DFF3C;
        font-family: 'Manrope', sans-serif;
        line-height: 1;
    }
    .metric-label {
        font-size: 11px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #ABABA8;
        margin-top: 8px;
        font-weight: 600;
    }
    .section-label {
        font-size: 10px;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        color: #ABABA8;
        font-weight: 700;
        margin-bottom: 12px;
    }
    .feedback-card {
        background: #121412;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
        border-left: 3px solid #5DFF3C;
    }
    .feedback-subject { font-weight: 700; color: #FAF9F5; font-size: 16px; }
    .feedback-meta { color: #ABABA8; font-size: 12px; margin-top: 4px; }
    .feedback-msg { color: #d1d1ce; margin-top: 12px; line-height: 1.6; }
    .brand-header {
        font-family: 'Manrope', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: #5DFF3C;
        letter-spacing: -1px;
    }
    .brand-sub {
        font-size: 10px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #ABABA8;
        font-weight: 600;
    }

    /* Style dataframe */
    .stDataFrame { border-radius: 12px; overflow: hidden; }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #5DFF3C, #3AF114) !important;
        color: #0D5D00 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 40px !important;
        padding: 12px 24px !important;
    }
    .stSidebar .stButton > button {
        display: block !important;
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        margin-bottom: 12px !important;
        background: #0B0D0B !important;
        color: #6BFF6B !important;
        border: 1px solid rgba(93, 255, 60, 0.45) !important;
        border-radius: 10px !important;
        padding: 14px 20px !important;
        box-shadow: inset 0 0 0 1px rgba(93,255,60,0.08) !important;
        text-align: left !important;
    }
    .stSidebar .stButton > button:hover {
        box-shadow: 0 0 20px rgba(93, 255, 60, 0.3) !important;
        transform: translateY(-1px);
        background: #0B0D0B !important;
    }
    .user-card {
        background: #121412;
        border: 1px solid #1F231F;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 18px;
    }
    .user-card-title {
        font-size: 16px;
        font-weight: 800;
        color: #FAF9F5;
        margin-bottom: 6px;
    }
    .user-card-meta {
        font-size: 12px;
        color: #ABABA8;
        margin-bottom: 16px;
    }
    .user-card-status {
        display: inline-block;
        color: #5DFF3C;
        background: rgba(93, 255, 60, 0.08);
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .user-card-actions {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
    }
</style>
""", unsafe_allow_html=True)


def api_get(endpoint):
    try:
        r = requests.get(f"{API_URL}{endpoint}", timeout=5)
        if r.status_code == 200:
            return r.json()
    except requests.ConnectionError:
        st.error("⚠️ Cannot connect to Floriety API. Make sure `python server.py` is running.")
    return None


def api_delete(endpoint):
    try:
        r = requests.delete(f"{API_URL}{endpoint}", timeout=5)
        return r.status_code == 200
    except:
        return False


def api_put(endpoint, data):
    try:
        r = requests.put(f"{API_URL}{endpoint}", json=data, timeout=5)
        return r.status_code == 200
    except:
        return False


MONTH_ORDER = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

MONTH_MAP = {m.lower(): i + 1 for i, m in enumerate(MONTH_ORDER)}


def normalize_month(value):
    if value is None:
        return None
    text = str(value).strip()

    # Directly parse year-month and datetime strings like "2024-05", "2024-05-18", or ISO datetimes.
    if '-' in text:
        date_part = text.split('T')[0].split(' ')[0]
        parts = date_part.split('-')
        if len(parts) >= 2 and parts[1].isdigit():
            month_number = int(parts[1])
            if 1 <= month_number <= 12:
                return MONTH_ORDER[month_number - 1]

    for fmt in ('%Y-%m', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return MONTH_ORDER[datetime.strptime(text, fmt).month - 1]
        except Exception:
            pass

    if text.isdigit():
        month_number = int(text)
        if 1 <= month_number <= 12:
            return MONTH_ORDER[month_number - 1]

    lower = text.lower()
    if lower in MONTH_MAP:
        return MONTH_ORDER[MONTH_MAP[lower] - 1]
    if len(lower) >= 3:
        for month in MONTH_ORDER:
            if month.lower().startswith(lower[:3]):
                return month

    return text.capitalize()


def prepare_month_dataframe(rows):
    rows = rows or []
    counts = {month: 0 for month in MONTH_ORDER}

    for row in rows:
        month = normalize_month(row.get('month'))
        if not month:
            continue
        value = row.get('count', 0) or 0
        try:
            count = int(float(value))
        except Exception:
            count = 0
        counts[month] = counts.get(month, 0) + count

    df = pd.DataFrame([
        {'month': month, 'count': counts[month]}
        for month in MONTH_ORDER
    ])
    df['count'] = df['count'].astype(int)
    return df


def get_chart_domain_and_step(df):
    max_count = int(df['count'].max()) if not df['count'].empty else 0
    if max_count <= 10:
        return 10, 1
    if max_count <= 100:
        return ((max_count + 9) // 10) * 10, 10
    if max_count <= 1000:
        return ((max_count + 99) // 100) * 100, 100
    return ((max_count + 999) // 1000) * 1000, 1000


def render_metric_chart(df, color):
    if alt is None:
        st.line_chart(df.set_index('month')['count'])
        return

    y_max, y_step = get_chart_domain_and_step(df)
    chart = alt.Chart(df).mark_line(point=True, interpolate='monotone', color=color, strokeWidth=3).encode(
        x=alt.X(
            'month:N',
            sort=MONTH_ORDER,
            axis=alt.Axis(labelAngle=-45, labelColor='#ABABA8', domain=False, tickColor='#4F574F')
        ),
        y=alt.Y(
            'count:Q',
            axis=alt.Axis(title='Count', titleColor='#ABABA8', labelColor='#ABABA8', domain=False, tickColor='#4F574F', tickMinStep=y_step),
            scale=alt.Scale(domain=[0, y_max], nice=False)
        ),
        tooltip=[
            alt.Tooltip('month:N', title='Month'),
            alt.Tooltip('count:Q', title='Count')
        ]
    ).properties(width='container', height=320)

    chart = chart.configure_view(strokeOpacity=0)
    st.altair_chart(chart, use_container_width=True)


# ─── Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="brand-header">🌿 Floriety</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Admin Dashboard</div>', unsafe_allow_html=True)
    st.markdown("---")
    if "page" not in st.session_state:
        st.session_state.page = "Analytics"

    if st.button("Analytics", key="nav_analytics"):
        st.session_state.page = "Analytics"
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

    if st.button("User Management", key="nav_users"):
        st.session_state.page = "User Management"
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

    if st.button("Feedback", key="nav_feedback"):
        st.session_state.page = "Feedback"

    page = st.session_state.page
    st.markdown("---")
    st.markdown('<div class="brand-sub">OWNER PANEL</div>', unsafe_allow_html=True)
    st.caption("Full authority over user accounts, system analytics, and feedback.")


# ═══════════════════════════════════════════════════════════════════
# ANALYTICS PAGE
# ═══════════════════════════════════════════════════════════════════
if page == "Analytics":
    st.markdown("## System Analytics")
    st.markdown('<div class="section-label">OVERVIEW</div>', unsafe_allow_html=True)

    analytics = api_get("/api/admin/analytics")
    if analytics:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'''<div class="metric-card">
                <div class="metric-value">{analytics["total_users"]}</div>
                <div class="metric-label">Total Users</div>
            </div>''', unsafe_allow_html=True)
        with c2:
            st.markdown(f'''<div class="metric-card">
                <div class="metric-value">{analytics["total_scans"]}</div>
                <div class="metric-label">Total Scans</div>
            </div>''', unsafe_allow_html=True)
        with c3:
            st.markdown(f'''<div class="metric-card">
                <div class="metric-value">{analytics["total_feedbacks"]}</div>
                <div class="metric-label">Feedback</div>
            </div>''', unsafe_allow_html=True)
        with c4:
            st.markdown(f'''<div class="metric-card">
                <div class="metric-value">{analytics["total_favorites"]}</div>
                <div class="metric-label">Favorites</div>
            </div>''', unsafe_allow_html=True)

        st.markdown("")
        st.markdown("")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="section-label">MONTHLY REGISTRATIONS</div>', unsafe_allow_html=True)
            user_df = prepare_month_dataframe(analytics.get("monthly_users", []))
            render_metric_chart(user_df, "#5DFF3C")
            st.markdown('<div class="section-label">REGISTRATIONS TABLE</div>', unsafe_allow_html=True)
            st.dataframe(
                user_df.rename(columns={'count': 'Registrations'}),
                use_container_width=True,
                hide_index=True,
            )

        with col2:
            st.markdown('<div class="section-label">MONTHLY SCANS</div>', unsafe_allow_html=True)
            scan_df = prepare_month_dataframe(analytics.get("monthly_scans", []))
            render_metric_chart(scan_df, "#3AF114")
            st.markdown('<div class="section-label">SCANS TABLE</div>', unsafe_allow_html=True)
            st.dataframe(
                scan_df.rename(columns={'count': 'Scans'}),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("")
        st.markdown('<div class="section-label">MONTHLY REGISTRATIONS vs SCANS</div>', unsafe_allow_html=True)
        joint_df = pd.merge(
            user_df.rename(columns={'count': 'Registrations'}),
            scan_df.rename(columns={'count': 'Scans'}),
            on='month',
        )
        st.dataframe(joint_df, use_container_width=True, hide_index=True)

        st.markdown('')
        st.markdown('<div class="section-label">TOP SCANNED FLOWERS</div>', unsafe_allow_html=True)
        if analytics["top_flowers"]:
            df = pd.DataFrame(analytics["top_flowers"])
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={"name": "Flower", "count": "Times Scanned"})
        else:
            st.info("No scans recorded yet.")


# ═══════════════════════════════════════════════════════════════════
# USER MANAGEMENT PAGE
# ═══════════════════════════════════════════════════════════════════
elif page == "User Management":
    st.markdown("## User Management")
    st.markdown('<div class="section-label">ALL REGISTERED USERS</div>', unsafe_allow_html=True)

    users = api_get("/api/admin/users")
    if users is not None:
        if len(users) == 0:
            st.info("No users registered yet. Showing sample user previews for layout.")
            users = [
                {"id": 101, "email": "amelia@floriety.ai", "created_at": "2026-02-18"},
                {"id": 102, "email": "noah@floriety.ai", "created_at": "2026-03-02"},
                {"id": 103, "email": "sam@floriety.ai", "created_at": "2026-03-28"},
            ]

        for user in users:
            user_name = user['email'].split('@')[0]
            joined_at = user.get('created_at', 'N/A')

            st.markdown(f"**{user_name}** | {user['email']} | Joined at: {joined_at}")

            with st.expander(f"✏️ Edit {user_name}", expanded=False):
                new_email = st.text_input("Email", value=user['email'], key=f"email_{user['id']}")
                new_password = st.text_input("New password", value='', type='password', key=f"password_{user['id']}")

                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.button("Save Changes", key=f"save_{user['id']}"):
                        payload = {'email': new_email}
                        if new_password:
                            payload['password'] = new_password
                        if api_put(f"/api/admin/users/{user['id']}", payload):
                            st.success("User updated!")
                            st.rerun()
                        else:
                            st.error("Failed to update user.")
                with ec2:
                    if st.button("Delete User", key=f"del_{user['id']}"):
                        st.session_state[f"confirm_del_{user['id']}"] = True

                    if st.session_state.get(f"confirm_del_{user['id']}", False):
                        st.warning(f"Are you sure you want to delete **{user['email']}**?")
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            if st.button("Yes, Delete", key=f"yes_del_{user['id']}"):
                                if api_delete(f"/api/admin/users/{user['id']}"):
                                    st.success("User deleted.")
                                    st.session_state[f"confirm_del_{user['id']}"] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to delete.")
                        with dc2:
                            if st.button("Cancel", key=f"no_del_{user['id']}"):
                                st.session_state[f"confirm_del_{user['id']}"] = False
                                st.rerun()

            st.divider()


# ═══════════════════════════════════════════════════════════════════
# FEEDBACK BOARD PAGE
# ═══════════════════════════════════════════════════════════════════
elif page == "Feedback":
    st.markdown("## Feedback Board")
    st.markdown('<div class="section-label">USER FEEDBACK</div>', unsafe_allow_html=True)

    feedback_list = api_get("/api/feedback")
    if feedback_list is not None:
        if len(feedback_list) == 0:
            st.info("No feedback received yet.")
        else:
            for fb in feedback_list:
                st.markdown(f'''<div class="feedback-card">
                    <div class="feedback-subject">{fb["subject"]}</div>
                    <div class="feedback-meta">
                        From: {fb.get("gmail", "") or fb["user_email"]}  ·  {fb["created_at"]}
                    </div>
                    <div class="feedback-msg">{fb["message"]}</div>
                </div>''', unsafe_allow_html=True)
