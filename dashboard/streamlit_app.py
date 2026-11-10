import random

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Release dashboard", layout="wide")

# OpenRun did the login. The app only reads who the request is from.
user = st.context.headers.get("X-Openrun-User", "anonymous")

st.title("Release dashboard")
st.caption(f"Signed in as {user}")

rng = random.Random(7)
days = pd.date_range(end=pd.Timestamp.today().normalize(), periods=30)
df = pd.DataFrame(
    {
        "deploys": [rng.randint(2, 14) for _ in days],
        "lead time (hours)": [round(rng.uniform(1.5, 9.0), 1) for _ in days],
        "rollbacks": [rng.choice([0, 0, 0, 0, 1]) for _ in days],
    },
    index=days,
)

c1, c2, c3 = st.columns(3)
c1.metric("Deploys, last 30 days", int(df["deploys"].sum()))
c2.metric("Median lead time", f"{df['lead time (hours)'].median():.1f} h")
c3.metric("Rollbacks", int(df["rollbacks"].sum()))

left, right = st.columns(2)
left.subheader("Deploys per day")
left.bar_chart(df["deploys"])
right.subheader("Lead time for changes")
right.line_chart(df["lead time (hours)"])
