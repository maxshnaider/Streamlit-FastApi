import os
import requests
import streamlit as st

API_URL = os.getenv("ADVISOR_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Crypto Advisor", layout="centered")
st.title("Crypto Trading Advisor")

coin = st.selectbox("Select coin", ["BTC", "ETH", "SOL"], index=0)
model_labels = {
    "Gemini Flash": "models/gemini-2.5-flash",
    "OpenAI gpt-4o-mini": "gpt-4o-mini",
}
model_label = st.selectbox("Select model", list(model_labels.keys()), index=0)
model = model_labels[model_label]

col1, col2 = st.columns(2)

with col1:
    if st.button("Calculate cost"):
        with st.spinner("Estimating cost..."):
            try:
                r = requests.get(
                    f"{API_URL}/estimate",
                    params={"coin": coin, "model": model},
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                st.subheader("Estimated cost (tiktoken)")
                st.metric("Estimated cost", f"${data.get('estimated_cost_usd', 0):.6f}")
            except Exception as e:
                st.error(f"Error: {e}")

with col2:
    if st.button("Get advice"):
        with st.spinner("Generating advice..."):
            try:
                r = requests.get(
                    f"{API_URL}/advice",
                    params={"coin": coin, "model": model},
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                st.subheader("Advice")
                st.write(data.get("reply", ""))
                st.metric("Actual cost", f"${data.get('estimated_cost_usd', 0):.6f}")
            except Exception as e:
                st.error(f"Error: {e}")
