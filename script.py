import streamlit as st
import pandas as pd
import datetime
import os
import io
import matplotlib.pyplot as plt
import altair as alt
import plotly.express as px
import subprocess
import sys

CSV_FILE = "leetcode_submissions.csv"
TARGET = 500
WEEKLY_GOAL = 50
MONTHLY_GOAL = 200

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Example usage
install("matplotlib")
install("plotly")
install("altair")

def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        return df.sort_values(by='date')
    else:
        return pd.DataFrame(columns=['date', 'count'])

def save_data(df):
    df.to_csv(CSV_FILE, index=False, date_format='%d-%m-%Y')

def add_submission(df, date, count):
    date = pd.to_datetime(date, dayfirst=True)
    if date in df['date'].values:
        df.loc[df['date'] == date, 'count'] += count
    else:
        df = pd.concat([df, pd.DataFrame([[date, count]], columns=['date', 'count'])])
    return df.sort_values(by='date')

def calculate_streak(df):
    df = df.sort_values(by='date', ascending=False)
    streak = 0
    today = datetime.date.today()
    for _, row in df.iterrows():
        if row['date'].date() == today:
            streak += 1
            today -= datetime.timedelta(days=1)
        elif row['date'].date() == today - datetime.timedelta(days=1):
            streak += 1
            today -= datetime.timedelta(days=1)
        else:
            break
    return streak

def missed_days(df, num_days=10):
    today = datetime.date.today()
    dates_set = set(df['date'].dt.date)
    missed = [today - datetime.timedelta(days=i) for i in range(1, num_days+1) if (today - datetime.timedelta(days=i)) not in dates_set]
    return missed

def filter_last_days(df, days):
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    return df[df['date'].dt.date >= cutoff]

def main():
    st.set_page_config(page_title="LeetCode Tracker", layout="centered", initial_sidebar_state="auto")
    st.markdown("""
        <style>
        body { color: white; background-color: #0e1117; }
        .stApp { background-color: #0e1117; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🧠 LeetCode Tracker")
    df = load_data()

    with st.form(key="submission_form"):
        count = st.number_input("Submissions today", min_value=0, step=1)
        submit = st.form_submit_button("Add")
        if submit and count > 0:
            df = add_submission(df, datetime.date.today(), count)
            save_data(df)
            st.success("Submission added!")

    total = df['count'].sum()
    progress = min((total / TARGET) * 100, 100)
    badge = "🧠 Newbie"
    if progress >= 100:
        badge = "🏆 Master"
    elif progress >= 75:
        badge = "💪 Expert"
    elif progress >= 50:
        badge = "🔥 Intermediate"
    elif progress >= 25:
        badge = "🌱 Beginner"

    streak = calculate_streak(df)

    st.metric(label="Total Submissions", value=total)
    st.progress(progress / 100)
    st.markdown(f"**Progress:** {progress:.1f}% — {badge}")
    st.markdown(f"🔥 **Streak:** {streak} day(s)")

    # Weekly/Monthly progress
    weekly = filter_last_days(df, 7)['count'].sum()
    monthly = filter_last_days(df, 30)['count'].sum()
    st.subheader("📈 Weekly & Monthly Goals")
    st.markdown(f"📅 This week: {weekly} / {WEEKLY_GOAL}")
    st.progress(min(weekly / WEEKLY_GOAL, 1.0))
    st.markdown(f"🗓️ This month: {monthly} / {MONTHLY_GOAL}")
    st.progress(min(monthly / MONTHLY_GOAL, 1.0))

    # Charts
    st.subheader("📊 Submissions Over Time")
    if not df.empty:
        filter_option = st.selectbox("📆 Filter Data", ["All Time", "Last 30 Days", "This Year"])
        df_graph = df.copy()
        df_graph = df_graph.groupby('date').sum().sort_index()
        today = datetime.date.today()
        if filter_option == "Last 30 Days":
            cutoff = today - datetime.timedelta(days=30)
            df_graph = df_graph[df_graph.index.date >= cutoff]
        elif filter_option == "This Year":
            df_graph = df_graph[df_graph.index.year == today.year]

        df_graph['Rolling Avg (7d)'] = df_graph['count'].rolling(7).mean()
        df_graph['Cumulative'] = df_graph['count'].cumsum()

        st.markdown("**📈 Daily Submissions & 7-Day Rolling Avg**")
        st.line_chart(df_graph[['count', 'Rolling Avg (7d)']], use_container_width=True)

        st.markdown("**🏁 Cumulative Submissions with Milestones**")
        chart_df = df_graph.reset_index().rename(columns={'date': 'Date'})
        base = alt.Chart(chart_df).mark_line().encode(
            x='Date:T',
            y=alt.Y('Cumulative:Q', title='Cumulative Submissions')
        ).properties(width=700, height=300)

        milestones = alt.Chart(pd.DataFrame({
            'Milestone': ['100', '250', '500'],
            'Value': [100, 250, 500]
        })).mark_rule(strokeDash=[5,5], color='orange').encode(
            y='Value:Q',
            tooltip=['Milestone']
        )

        st.altair_chart(base + milestones, use_container_width=True)

        # Plotly chart for export and hover
        st.markdown("**📤 Export Cumulative Chart**")
        plotly_fig = px.line(chart_df, x="Date", y="Cumulative", title="Cumulative Submissions Over Time")
        plotly_fig.add_hline(y=100, line_dash="dot", line_color="orange", annotation_text="100")
        plotly_fig.add_hline(y=250, line_dash="dot", line_color="orange", annotation_text="250")
        plotly_fig.add_hline(y=500, line_dash="dot", line_color="green", annotation_text="500")
        st.plotly_chart(plotly_fig, use_container_width=True)

        # Export chart as PNG
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(chart_df["Date"], chart_df["Cumulative"], marker='o', color='skyblue', linewidth=2)
        ax.set_title("Cumulative LeetCode Submissions")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative")
        ax.axhline(y=100, color='orange', linestyle='--')
        ax.axhline(y=250, color='orange', linestyle='--')
        ax.axhline(y=500, color='green', linestyle='--')

        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png")
        st.download_button("📸 Download Chart as PNG", buf.getvalue(), file_name="leetcode_chart.png", mime="image/png")
    else:
        st.info("No data yet. Add submissions or sync with LeetCode to see the graph.")

    st.subheader("📅 Daily Log")
    st.dataframe(df.sort_values(by='date', ascending=False).reset_index(drop=True))

    st.subheader("🚫 Missed Days (Last 10)")
    missed = missed_days(df)
    st.text("\n".join([d.strftime('%d-%m-%Y') for d in missed]))

    csv = df.copy()
    csv['date'] = csv['date'].dt.strftime('%d-%m-%Y')
    st.download_button("📥 Download CSV", csv.to_csv(index=False), file_name="leetcode_submissions.csv", mime="text/csv")

    st.subheader("🔔 Reminders")
    st.info("Don't forget to submit your daily progress! Set an alarm or calendar event.")

    # st.subheader("📤 Sync to GitHub")
    # st.caption("Coming soon: Auto-sync with your GitHub repo for backups.")
    #
    # st.subheader("📱 Installable App")
    # st.markdown("This web app is a PWA — try deploying via [Streamlit Share](https://share.streamlit.io) and install on your device!")

if __name__ == '__main__':
    main()
