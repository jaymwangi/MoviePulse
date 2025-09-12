# utils/settings_handler.py
import streamlit as st
from session_utils.user_profile import (
    set_theme, set_font, set_spoiler_free, set_dyslexia_mode,
    set_critic_mode_pref, set_preference
)

def handle_settings_change(setting_key: str, new_value):
    """Handle settings changes and apply them globally"""
    setting_handlers = {
        "theme": set_theme,
        "font": set_font,
        "spoiler_free": set_spoiler_free,
        "dyslexia_mode": set_dyslexia_mode,
        "critic_mode": set_critic_mode_pref
    }
    
    if setting_key in setting_handlers:
        setting_handlers[setting_key](new_value)
        
        # For theme/font changes, reapply styling
        if setting_key in ["theme", "font", "dyslexia_mode"]:
            # Import here to avoid circular imports
            from utils.theme_applier import apply_theme_settings, inject_custom_css
            apply_theme_settings()
            inject_custom_css()
            
        st.success(f"Settings updated successfully!")
        st.rerun()
    else:
        # Generic preference handler
        set_preference(setting_key, new_value)