import streamlit as st
from typing import Optional

def back_button(
    target_page: str,
    label: str = "← Back",
    key: Optional[str] = None,
    use_session_state: bool = True,
    **button_kwargs
):
    """
    Creates a consistent back button that navigates to a specified page.
    
    Args:
        target_page (str): The page name to navigate back to (e.g., "Home")
        label (str): Button label (defaults to ← Back)
        key (str, optional): Unique key for Streamlit button
        use_session_state (bool): If True, uses session_state for navigation
        **button_kwargs: Additional styling arguments for st.button
        
    Example:
        back_button("Home", label="Go Back", use_container_width=True)
    """
    default_kwargs = {
        "type": "secondary",
        "use_container_width": True,
    }
    
    # Merge default and user-provided kwargs
    final_kwargs = {**default_kwargs, **button_kwargs}
    
    if st.button(label, key=key, **final_kwargs):
        if use_session_state:
            st.session_state.current_page = target_page
        else:
            st.experimental_set_query_params(page=target_page)
        
        # Force a rerun to trigger the page change
        st.experimental_rerun()

def back_button_style():
    """
    Applies consistent CSS styling for back buttons across the app.
    Called once in your main app configuration.
    """
    st.markdown(
        """
        <style>
        /* Consistent back button styling */
        div.stButton > button:first-child {
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        div.stButton > button:first-child:hover {
            transform: translateX(-3px);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
