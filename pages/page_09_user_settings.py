# pages/page_09_user_settings.py
import streamlit as st

def main():
    # Import theme_applier directly (bypassing utils.__init__)
    import sys
    from pathlib import Path
    
    # Add the utils directory to path if needed
    utils_path = Path(__file__).parent.parent / "utils"
    if str(utils_path) not in sys.path:
        sys.path.insert(0, str(utils_path))
    
    # Import theme_applier module directly
    from utils.theme_applier import apply_theme_settings
    
    # Apply theme before rendering anything
    apply_theme_settings()
    
    # Now import SettingsPanel (after theme is applied)
    from ui_components.SettingsPanel import render_settings_panel
    
    # Page configuration
    st.set_page_config(
        page_title="MoviePulse - Settings",
        page_icon="⚙️",
        layout="wide"
    )
    
    # Page header
    st.title("⚙️ User Settings")
    st.markdown("Customize your MoviePulse experience with these settings.")
    
    # Render the settings panel
    render_settings_panel()
    
    # Add some helpful information
    st.divider()
    st.subheader("ℹ️ About These Settings")
    
    with st.expander("How settings affect your experience"):
        st.markdown("""
        - **Theme**: Changes the color scheme of the entire application
        - **Font Preference**: Adjusts text appearance for better readability
        - **Critic Personality**: Influences which movies are recommended to you
        - **Spoiler-Free Mode**: Hides potentially revealing information about movies
        - **Dyslexia-Friendly Font**: Uses OpenDyslexic font to improve readability
        - **Notifications**: Controls whether you receive update notifications
        """)
    
    # Add sidebar navigation back to home
    with st.sidebar:
        st.page_link("app.py", label="← Back to Home", icon="🏠")

if __name__ == "__main__":
    main()