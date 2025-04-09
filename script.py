import streamlit as st
import pandas as pd
import datetime
import os
from streamlit.components.v1 import html

CSV_FILE = "leetcode_submissions.csv"
TARGET = 500

WEEKLY_GOAL = 50
MONTHLY_GOAL = 200

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

def missed_days(df, num_days=100):
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

    st.subheader("📅 Daily Log")
    st.dataframe(df.sort_values(by='date', ascending=False).reset_index(drop=True))

    st.subheader("🚫 Missed Days (Last 100)")
    missed = missed_days(df)
    st.text("\n".join([d.strftime('%d-%m-%Y') for d in missed]))

    csv = df.copy()
    csv['date'] = csv['date'].dt.strftime('%d-%m-%Y')
    st.download_button("📥 Download CSV", csv.to_csv(index=False), file_name="leetcode_submissions.csv", mime="text/csv")

    st.subheader("🔔 Reminders")
    st.info("Don't forget to submit your daily progress! Set an alarm or calendar event.")

    st.subheader("📤 Sync to GitHub")
    st.caption("Coming soon: Auto-sync with your GitHub repo for backups.")

    st.subheader("📱 Installable App")
    st.markdown("This web app is a PWA — try deploying via [Streamlit Share](https://share.streamlit.io) and install on your device!")

if __name__ == '__main__':
    main()