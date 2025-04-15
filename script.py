import requests
import streamlit as st
import pandas as pd
import datetime
import os
import io
import matplotlib.pyplot as plt
import altair as alt
import plotly.express as px

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
        return pd.DataFrame(columns=['date', 'count', 'Manual count'])

def save_data(df):
    df.to_csv(CSV_FILE, index=False, date_format='%d-%m-%Y')

def add_submission(df, date, count, manual=False):
    date = pd.to_datetime(date, dayfirst=True)

    if date in df['date'].values:
        existing_count = df.loc[df['date'] == date, 'count'].values[0]
        if manual:
            # Ensure 'Manual count' is initialized properly
            df.loc[df['date'] == date, 'Manual count'] = df.loc[df['date'] == date, 'Manual count'].fillna(0) + count
        if existing_count < count:
            df.loc[df['date'] == date, 'count'] = count

    else:
        new_row = {
            'date': date,
            'count': 0,
            'Manual count': 0
        }
        if manual:
            new_row['Manual count'] = count
        else:
            new_row['count'] = count
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    return df.sort_values(by='date')


def calculate_streak(df):
    df = df.sort_values(by='date', ascending=False)
    streak = 0
    today = datetime.date.today()

    for _, row in df.iterrows():
        row_date = row['date'].date()
        if row_date == today:
            streak += 1
            today -= datetime.timedelta(days=1)
        else:
            break  # as soon as we hit a missing day, stop

    return streak

def missed_days(df, num_days=10):
    today = datetime.date.today()
    dates_set = set(df['date'].dt.date)
    missed = [today - datetime.timedelta(days=i) for i in range(1, num_days+1) if (today - datetime.timedelta(days=i)) not in dates_set]
    return missed

def get_current_week_data(df):
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + datetime.timedelta(days=6)  # Sunday
    return df[(df['date'].dt.date >= start_of_week) & (df['date'].dt.date <= end_of_week)]

def get_current_month_data(df):
    today = datetime.date.today()
    start_of_month = datetime.date(today.year, today.month, 1)
    return df[(df['date'].dt.date >= start_of_month) & (df['date'].dt.date <= today)]

def get_monthly_heatmap_data(df):
    # Ensure the 'date' column is in datetime format
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Get today's date and the start of the current month
    today = datetime.date.today()
    start_of_month = datetime.date(today.year, today.month, 1)
    end_of_month = today

    # Filter the data for the current month
    month_df = df[(df['date'].dt.date >= start_of_month) & (df['date'].dt.date <= end_of_month)]

    # Group by the date and sum the 'count' for each date
    heatmap_df = month_df.groupby(df['date'].dt.date)['count'].sum().reset_index()
    heatmap_df.columns = ['date', 'submissions']

    # Create a complete range of dates for the month
    all_days = pd.date_range(start=start_of_month, end=end_of_month)
    full_df = pd.DataFrame({'date': all_days})
    full_df['date'] = full_df['date'].dt.date

    # Merge the full range of days with the submissions data
    merged_df = full_df.merge(heatmap_df, on='date', how='left').fillna(0)
    merged_df['submissions'] = merged_df['submissions'].astype(int)

    return merged_df

def create_green_heatmap(df):
    monthly_heatmap_df = get_monthly_heatmap_data(df)

    fig = px.imshow(
        [monthly_heatmap_df['submissions'].tolist()],
        labels=dict(x="", y=""),
        x=monthly_heatmap_df['date'].astype(str),
        color_continuous_scale='greens',
        aspect="auto",
        text_auto=True
    )

    fig.update_layout(
        title="📅 Daily Submissions Heatmap (This Month)",
        xaxis_title="",
        yaxis_showticklabels=False,
        coloraxis_showscale=False,
        height=250,
        xaxis=dict(
            tickmode='array',
            tickvals=monthly_heatmap_df['date'].astype(str),
            tickangle=-45
        ),
        margin=dict(t=30, b=30, l=10, r=10)
    )

    st.plotly_chart(fig, use_container_width=True)

def fetch_leetcode_data(username):
    url = "https://leetcode.com/graphql"
    headers = {
        "Content-Type": "application/json",
        "Referer": f"https://leetcode.com/{username}/"
    }

    query = {
        "operationName": "getUserProfile",
        "variables": {"username": username},
        "query": """
        query getUserProfile($username: String!) {
          allQuestionsCount {
            difficulty
            count
          }
          matchedUser(username: $username) {
            submitStats {
              acSubmissionNum {
                difficulty
                count
              }
            }
            userCalendar {
              submissionCalendar
            }
          }
        }
        """
    }

    response = requests.post(url, json=query, headers=headers)
    if response.status_code != 200:
        st.error("Failed to fetch LeetCode data. Check username or try later.")
        return {}, {}

    data = response.json()["data"]
    calendar = eval(data["matchedUser"]["userCalendar"]["submissionCalendar"])
    daily_counts = {
        datetime.date.fromtimestamp(int(ts)): count for ts, count in calendar.items()
    }

    stats = data["matchedUser"]["submitStats"]["acSubmissionNum"]
    solved = {item["difficulty"]: item["count"] for item in stats}
    all_qs = {entry["difficulty"]: entry["count"] for entry in data["allQuestionsCount"]}

    return daily_counts, solved, all_qs

def main():
    st.set_page_config(page_title="LeetCode Tracker", layout="centered", initial_sidebar_state="auto")
    st.markdown("""
        <style>
        body { color: white; background-color: #0e1117; }
        .stApp { background-color: #0e1117; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🧠 LeetCode Tracker")
    st.subheader("🔄 Auto Sync with LeetCode")
    
    df = load_data()

    username = 'ltandon'

    if username:
        try:
            submission_data, solved_qs, all_qs = fetch_leetcode_data(username)
            for date, count in submission_data.items():
                df = add_submission(df, date, count, False)
            save_data(df)
            st.success("LeetCode data synced!")
            name = {"Easy":"🟢 **Easy:**", "Medium":"🟡 **Medium:**", "Hard":"🔴 **Hard:**"}
            for diff in ["Easy", "Medium", "Hard"]:
                total_question = all_qs.get(diff, 0)
                solved = solved_qs.get(diff, 0)
                percent = solved / total_question if total_question else 0

                st.subheader(f"{name.get(diff)} Problems")
                st.text(f"{solved} / {total_question} solved")
                st.progress(percent)

            # Overall progress
            total_all = all_qs.get('All')
            solved_all = solved_qs.get('All')
            st.subheader("🌟 Overall Progress")
            st.text(f"{solved_all} / {total_all} solved")
            st.progress(solved_all / total_all)

        except Exception as e:
            st.error("Error fetching data from LeetCode. Please check your username or try again later.")
            st.code(str(e))

    with st.form(key="submission_form"):
        count = st.number_input("Submissions today", min_value=0, step=1)
        submit = st.form_submit_button("Add")
        if submit and count > 0:
            df = add_submission(df, datetime.date.today(), count, True)
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
    weekly = get_current_week_data(df)['count'].sum()
    monthly = get_current_month_data(df)['count'].sum()
    st.subheader("📈 Weekly & Monthly Goals")
    st.markdown(f"📅 This week (Mon–Sun): {weekly} / {WEEKLY_GOAL}")
    st.progress(min(weekly / WEEKLY_GOAL, 1.0))
    st.markdown(f"🗓️ This month (April): {monthly} / {MONTHLY_GOAL}")
    st.progress(min(monthly / MONTHLY_GOAL, 1.0))

    create_green_heatmap(df)

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

if __name__ == '__main__':
    main()
