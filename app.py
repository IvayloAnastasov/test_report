import streamlit as st

st.set_page_config(page_title="Simple Greeting App")

st.title("👋 Hello App")

name = st.text_input("Enter your name:")

if st.button("Say Hello"):
    if name:
        st.success(f"Hello, {name}!")
    else:
        st.warning("Please enter your name.")
