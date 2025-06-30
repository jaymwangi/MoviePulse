import streamlit as st

def update_query_params(params: dict):
    """
    Update query parameters without page reload
    Args:
        params: Dictionary of parameters to update
    """
    current_params = st.query_params.to_dict()
    current_params.update(params)
    st.query_params.clear()
    st.query_params.update(**current_params)