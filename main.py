import streamlit as st
import requests

st.title("Calculator")

a = st.number_input("First", 0)
b = st.number_input("Second", 0)

if st.button("Go"):
    r = requests.get("http://127.0.0.1:8000/sum", params={"a": a, "b": b})
    st.write("Result:", r.json()["result"])
