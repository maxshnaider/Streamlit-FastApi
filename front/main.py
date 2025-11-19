import os
import requests
import streamlit as st

API_URL = os.getenv("ADVISOR_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Crypto Advisor", layout="wide")

ss = st.session_state
ss.setdefault("auth", False)
ss.setdefault("u", "")
ss.setdefault("p", "")
ss.setdefault("bal", 0.0)
ss.setdefault("cap", 0.0)
ss.setdefault("reply", "")
ss.setdefault("est_cost", None)
ss.setdefault("est_pred", None)
ss.setdefault("last_cost", None)


def api_get(path: str, params: dict | None = None, timeout: int = 20) -> dict:
    r = requests.get(f"{API_URL}{path}", params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def api_post(path: str, data: dict | None = None, timeout: int = 20) -> dict:
    r = requests.post(f"{API_URL}{path}", data=data or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def show_err(e: Exception) -> None:
    try:
        st.error(e.response.json().get("detail", str(e)))  # type: ignore[attr-defined]
    except Exception:
        st.error(str(e))


with st.sidebar:
    st.markdown("### User")

    if not ss["auth"]:
        u = st.text_input("Username", value="admin")
        p = st.text_input("Password", type="password", value="admin")

        if st.button("Sign in", use_container_width=True):
            try:
                api_post("/login", {"username": u, "password": p})
                ss["auth"], ss["u"], ss["p"] = True, u, p

                info = api_get(
                    "/user",
                    {"username": ss["u"], "password": ss["p"]},
                )
                ss["bal"] = float(info.get("balance_usd", 0.0))
                ss["cap"] = float(info.get("initial_balance_usd", ss["bal"]))
                st.rerun()
            except Exception as e:
                show_err(e)

        st.stop()

    st.markdown(f"**{ss['u']}**")
    if st.button("Logout", use_container_width=True):
        for key in (
            "auth",
            "u",
            "p",
            "bal",
            "cap",
            "reply",
            "est_cost",
            "est_pred",
            "last_cost",
        ):
            ss.pop(key, None)
        st.rerun()

    show_balance = st.checkbox("👁 Show balance", value=True)

    cap = max(ss["cap"], 1e-9)
    pct = max(0.0, min(ss["bal"] / cap, 1.0))

    if show_balance:
        st.markdown(f"**Balance:** {ss['bal']:.6f} / {cap:.6f}")
    else:
        st.markdown("**Balance:** ••••• / •••••")

    st.progress(pct)


st.title("Crypto Trading Advisor")

coin = st.selectbox("Select coin", ["BTC", "ETH", "SOL"], index=0)

model_labels = {
    "Gemini Flash": "models/gemini-2.5-flash",
    "OpenAI gpt-4o-mini": "gpt-4o-mini",
}
model_label = st.selectbox("Select model", list(model_labels.keys()), index=0)
model = model_labels[model_label]

c1, c2 = st.columns(2)

with c1:
    if st.button("Estimate cost", use_container_width=True):
        try:
            d = api_get(
                "/estimate",
                params={
                    "coin": coin,
                    "model": model,
                    "username": ss["u"],
                    "password": ss["p"],
                },
                timeout=20,
            )
            ss["est_cost"] = float(d.get("estimated_cost_usd", 0.0))
            ss["est_pred"] = float(d.get("predicted_balance_usd", 0.0))
        except Exception as e:
            show_err(e)

with c2:
    if st.button("Get advice", use_container_width=True):
        try:
            d = api_get(
                "/advice",
                params={
                    "coin": coin,
                    "model": model,
                    "username": ss["u"],
                    "password": ss["p"],
                },
                timeout=60,
            )

            ss["reply"] = d.get("reply", "")

            cost = float(d.get("deducted_usd", 0.0))
            new_balance = float(d.get("user_balance_usd", ss["bal"]))

            ss["last_cost"] = cost
            ss["bal"] = new_balance

            st.rerun()

        except Exception as e:
            show_err(e)

if ss["est_cost"] is not None:
    st.subheader("Estimate")
    st.metric("Estimated cost", f"${ss['est_cost']:.6f}")
    st.metric("Predicted balance", f"${ss['est_pred']:.6f}")

if ss["reply"]:
    st.subheader("Advice")
    st.write(ss["reply"])

    if ss["last_cost"] is not None:
        st.metric("Cost this advice", f"${ss['last_cost']:.6f}")
        st.metric("Current balance", f"${ss['bal']:.6f}")
