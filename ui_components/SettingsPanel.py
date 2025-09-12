# ui_components/SettingsPanel.py
import streamlit as st
from core_config.constants import THEME_OPTIONS, FONT_OPTIONS, CRITIC_MODE_OPTIONS
from session_utils.user_profile import (
    get_theme, get_font, is_spoiler_free, is_dyslexia_mode,
    get_critic_mode_pref, load_user_preferences, save_user_preferences, DEFAULT_PREFERENCES
)
from utils.settings_handler import handle_settings_change

# Try different import approaches
try:
    from utils.accessibility_helper import apply_accessibility_settings
except ImportError:
    # Fallback import for different project structure
    try:
        from ..utils.accessibility_helper import apply_accessibility_settings
    except ImportError:
        # Define a fallback function if the import still fails
        def apply_accessibility_settings():
            """Fallback function if accessibility helper cannot be imported"""
            pass

def render_settings_panel():
    """Render the comprehensive settings panel"""
    st.header("⚙️ User Settings")
    
    # Load current preferences
    prefs = load_user_preferences()
    
    # Theme Settings
    with st.expander("🎨 Theme & Appearance", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            current_theme = get_theme()
            new_theme = st.selectbox(
                "Color Theme",
                options=THEME_OPTIONS,
                index=THEME_OPTIONS.index(current_theme),
                key="theme_select",
                help="Choose between dark, light, or system theme"
            )
            if new_theme != current_theme:
                handle_settings_change("theme", new_theme)
        
        with col2:
            current_font = get_font()
            new_font = st.selectbox(
                "Font Preference",
                options=FONT_OPTIONS,
                index=FONT_OPTIONS.index(current_font),
                key="font_select",
                help="Choose default, dyslexia-friendly, or large text font"
            )
            if new_font != current_font:
                handle_settings_change("font", new_font)
    
    # Accessibility Settings
    with st.expander("♿ Accessibility", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            current_spoiler = is_spoiler_free()
            new_spoiler = st.toggle(
                "Spoiler-Free Mode",
                value=current_spoiler,
                key="spoiler_toggle",
                help="Hide potential spoilers in movie descriptions and details"
            )
            if new_spoiler != current_spoiler:
                handle_settings_change("spoiler_free", new_spoiler)
                # Apply immediately
                apply_accessibility_settings()
            
            # Add high contrast mode toggle
            high_contrast = prefs.get("high_contrast", False)
            new_high_contrast = st.toggle(
                "High Contrast Mode",
                value=high_contrast,
                key="high_contrast_toggle",
                help="Increase contrast for better visibility"
            )
            if new_high_contrast != high_contrast:
                handle_settings_change("high_contrast", new_high_contrast)
                apply_accessibility_settings()
        
        with col2:
            current_dyslexia = is_dyslexia_mode()
            new_dyslexia = st.toggle(
                "Dyslexia-Friendly Mode",
                value=current_dyslexia,
                key="dyslexia_toggle",
                help="Use OpenDyslexic font and improved readability settings"
            )
            if new_dyslexia != current_dyslexia:
                handle_settings_change("dyslexia_mode", new_dyslexia)
                # Apply immediately
                apply_accessibility_settings()
    
    # Recommendation Settings
    with st.expander("🎬 Recommendation Preferences", expanded=True):
        current_critic = get_critic_mode_pref()
        new_critic = st.selectbox(
            "Critic Personality",
            options=CRITIC_MODE_OPTIONS,
            index=CRITIC_MODE_OPTIONS.index(current_critic),
            key="critic_select",
            help="Choose which critic's perspective to use for recommendations"
        )
        if new_critic != current_critic:
            handle_settings_change("critic_mode", new_critic)
    
    # Notifications
    with st.expander("🔔 Notifications"):
        notifications = prefs.get("notifications_enabled", True)
        new_notifications = st.toggle(
            "Enable Notifications",
            value=notifications,
            key="notifications_toggle",
            help="Show toast notifications for new features and updates"
        )
        if new_notifications != notifications:
            handle_settings_change("notifications_enabled", new_notifications)
    
    # Data Management
    with st.expander("💾 Data Management"):
        st.info("Your preferences are automatically saved locally.")
        
        if st.button("Export Preferences", help="Download your settings as a JSON file"):
            import json
            from datetime import datetime
            
            export_data = {
                "export_date": datetime.now().isoformat(),
                "preferences": prefs
            }
            
            st.download_button(
                label="Download Preferences",
                data=json.dumps(export_data, indent=2),
                file_name=f"moviepulse_preferences_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        
        if st.button("Reset to Defaults", type="secondary", help="Restore all settings to default values"):
            save_user_preferences(DEFAULT_PREFERENCES.copy())
            st.success("Settings reset to defaults!")
            st.rerun()

# For use in sidebar
def render_quick_settings():
    """Render a compact settings panel for sidebar"""
    st.sidebar.header("⚙️ Quick Settings")
    
    # Theme toggle
    current_theme = get_theme()
    theme_icon = "🌙" if current_theme == "dark" else "☀️"
    new_theme = st.sidebar.selectbox(
        "Theme",
        options=THEME_OPTIONS,
        index=THEME_OPTIONS.index(current_theme),
        label_visibility="collapsed"
    )
    if new_theme != current_theme:
        handle_settings_change("theme", new_theme)
    
    # Quick accessibility toggles
    col1, col2 = st.sidebar.columns(2)
    with col1:
        spoiler_status = "👁️✓" if is_spoiler_free() else "👁️✗"
        if st.button(spoiler_status, help="Toggle spoiler protection"):
            handle_settings_change("spoiler_free", not is_spoiler_free())
            apply_accessibility_settings()
    with col2:
        dyslexia_status = "♿✓" if is_dyslexia_mode() else "♿✗"
        if st.button(dyslexia_status, help="Toggle accessibility mode"):
            handle_settings_change("dyslexia_mode", not is_dyslexia_mode())
            apply_accessibility_settings()
    
    st.sidebar.divider()