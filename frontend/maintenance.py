"""Manual maintenance screen. Switched by MAINTENANCE_MODE, never by a network
read -- see landing.py._maintenance_on. If the switch itself is down, the app
must not be."""

import streamlit as st


def maintenance():
    st.title(":material/build: Under maintenance")
    st.info(
        "We're doing planned maintenance and will be back shortly. "
        "Your account, holdings and any scheduled rebalances are unaffected."
    )
    st.caption("If this is taking longer than expected, check back in a few minutes.")
