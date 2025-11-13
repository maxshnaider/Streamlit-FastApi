import os
import requests
import streamlit as st

API_URL = os.getenv("ADVISOR_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Crypto Advisor", layout="centered")
st.title("Crypto Trading Advisor")

ss = st.session_state
ss.setdefault("auth", False)
ss.setdefault("u", "")
ss.setdefault("p", "")
ss.setdefault("bal", 0.0)
ss.setdefault("cap", 0.0)
ss.setdefault("reply", "")


def api_get(path, params=None):
    r = requests.get(f"{API_URL}{path}", params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()


def api_post(path, data=None):
    r = requests.post(f"{API_URL}{path}", data=data or {}, timeout=20)
    r.raise_for_status()
    return r.json()


def show_err(e):
    try:
        st.error(e.response.json().get("detail", str(e)))
    except Exception:
        st.error(str(e))


if not ss["auth"]:
    u = st.text_input("Username (admin / user)", value="admin")
    p = st.text_input("Password", type="password", value="admin")
    if st.button("Sign in"):
        try:
            api_post("/login", {"username": u, "password": p})
            ss.update({"auth": True, "u": u, "p": p})
            st.rerun()
        except Exception as e:
            show_err(e)
    st.stop()

_, _, rcol = st.columns(3)
with rcol:
    st.write(f"**{ss['u']}**")
    if st.button("Logout"):
        ss.clear()
        st.rerun()

try:
    d = api_get("/user", {"username": ss["u"], "password": ss["p"]})
    ss["bal"] = float(d["balance_usd"])
    ss["cap"] = float(d["initial_balance_usd"])
except Exception as e:
    show_err(e)
    st.stop()

cap = max(ss["cap"], 1e-9)
pct = max(0.0, min(ss["bal"] / cap, 1.0))
st.markdown(f"**Balance:** ${ss['bal']:.6f} / ${cap:.6f}")
st.progress(pct)

coin = st.selectbox("Select coin", ["BTC", "ETH", "SOL"], 0)
model = st.selectbox("Select model", ["models/gemini-2.5-flash", "gpt-4o-mini"], 0)

c1, c2 = st.columns(2)

with c1:
    if st.button("Estimate cost"):
        try:
            d = api_get(
                "/estimate",
                {
                    "coin": coin,
                    "model": model,
                    "username": ss["u"],
                    "password": ss["p"],
                },
            )
            st.subheader("Estimate")
            st.metric("Estimated cost", f"${float(d['estimated_cost_usd']):.6f}")
            st.metric("Predicted balance", f"${float(d['predicted_balance_usd']):.6f}")
        except Exception as e:
            show_err(e)

with c2:
    if st.button("Get advice"):
        try:
            d = api_get(
                "/advice",
                {
                    "coin": coin,
                    "model": model,
                    "username": ss["u"],
                    "password": ss["p"],
                },
            )

            ss["reply"] = d.get("reply", "")
            st.subheader("Advice")
            st.write(ss["reply"])

            spent = float(d.get("deducted_usd", 0.0))
            left = float(d.get("user_balance_usd", ss["bal"]))
            m1, m2 = st.columns(2)
            m1.metric("Cost this query", f"${spent:.6f}")
            m2.metric("Remaining balance", f"${left:.6f}")

            ss["bal"] = left
            cap = max(ss["cap"], 1e-9)
            st.progress(min(left / cap, 1.0))

        except Exception as e:
            show_err(e)
