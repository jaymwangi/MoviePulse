# utils/spoiler_handler.py
import streamlit as st
from session_utils.user_profile import is_spoiler_free

def apply_spoiler_protection(content: str, is_spoiler: bool = False) -> str:
    """Apply spoiler protection to content if enabled"""
    if is_spoiler_free() and is_spoiler:
        return "🚫 **Spoiler content hidden**"
    return content

def spoiler_wrapper(func):
    """Decorator to automatically apply spoiler protection"""
    def wrapper(*args, **kwargs):
        if is_spoiler_free() and kwargs.get('contains_spoilers', False):
            return st.warning("Spoiler content is hidden in your current settings.")
        return func(*args, **kwargs)
    return wrapper

def render_spoiler_content(content, spoiler_type="general"):
    """
    Render content with spoiler protection if enabled
    
    Args:
        content: The content to render (text or Streamlit element)
        spoiler_type: Type of spoiler ("ending", "runtime", "plot", "general")
    
    Returns:
        Rendered content with spoiler protection if needed
    """
    if not is_spoiler_free():
        return content
    
    # Define spoiler warnings based on type
    warnings = {
        "ending": "⚠️ Contains ending information",
        "runtime": "⚠️ Contains runtime information",
        "plot": "⚠️ Contains plot details",
        "general": "⚠️ Potential spoiler content"
    }
    
    warning = warnings.get(spoiler_type, warnings["general"])
    
    # Create a collapsible section for spoiler content
    with st.expander(warning, expanded=False):
        st.write(content)
    
    return None

def spoiler_guard(func):
    """
    Decorator to protect functions that might display spoiler content
    """
    def wrapper(*args, **kwargs):
        if is_spoiler_free():
            st.warning("Spoiler-free mode is enabled. Some content may be hidden.")
            # You might want to return a placeholder or modified content
            return None
        return func(*args, **kwargs)
    return wrapper