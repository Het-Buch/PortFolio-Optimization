import streamlit as st
import database.register_user as rt
import pandas as pd


@st.cache_data
def load_pincode_data():
    return pd.read_csv("data/india_pincodes.csv", low_memory=False)


df = load_pincode_data()


def register():

    st.title("User Registration")

    # ----------------------
    # Basic Information
    # ----------------------
    st.subheader("Basic Information")

    email = st.text_input("Email")
    name = st.text_input("Name")
    col1, col2 = st.columns([1,4])

    with col1:
        st.text_input("Code", "+91", disabled=True)

    with col2:
        phone = st.text_input("Phone Number", max_chars=10)
        phone = "+91" + phone

    # ----------------------
    # Address
    # ----------------------
    st.subheader("Address")

    col1, col2 = st.columns(2)

    with col1:
        country = "India"
        st.text_input("Country", value=country, disabled=True)

    with col2:
        states = sorted(df["statename"].dropna().astype(str).unique())
        state = st.selectbox("State", states)
        state_df = df[df["statename"] == state]
    
    col3, col4 = st.columns(2)

    with col3:
        cities = sorted(state_df["district"].unique())
        city = st.selectbox("City", cities)
        city_df = state_df[state_df["district"] == city]

    with col4:
        areas = sorted(city_df["officename"].unique())
        area = st.selectbox("Area", areas)

    # Final filter for pincode
    area_df = city_df[city_df["officename"] == area]
    zip_code = city_df.loc[
        city_df["officename"] == area, "pincode"
    ].iloc[0]

    zip_code = int(zip_code)

    st.text_input("Pincode", value=str(zip_code), disabled=True)

    # ----------------------
    # Security
    # ----------------------
    st.subheader("Security")

    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    # ----------------------
    # Register Button
    # ----------------------
    if st.button("Register"):

        if not all([email, name, phone, password, confirm_password]):
            st.warning("Please fill all required fields.")
            return

        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        result = rt.register_user(
            email,
            password,
            name,
            phone,
            country,
            state,
            city,
            zip_code
        )

        if result and "successfully" in result.lower():
            st.success(result)
        else:
            st.error(result)

    st.divider()

    if st.button("Go to Login"):
        st.session_state["page"] = "login"
        st.rerun()


if __name__ == "__main__":
    register()