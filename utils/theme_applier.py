import streamlit as st
from pathlib import Path
from session_utils.user_profile import get_theme, get_font, is_dyslexia_mode

def apply_theme_settings():
    """Apply theme and font settings globally"""
    theme = get_theme()
    font = get_font()
    dyslexia_mode = is_dyslexia_mode()
    
    # Apply theme
    _apply_theme_css(theme)
    
    # Apply font settings
    _apply_font_css(font, dyslexia_mode)
    
    # Configure Streamlit theme options
    _configure_streamlit_theme(theme)

def _apply_theme_css(theme: str):
    """Inject theme CSS based on user preference"""
    css_file = f"media_assets/styles/theme_{theme}.css"
    
    try:
        if Path(css_file).exists():
            with open(css_file, 'r') as f:
                css_content = f.read()
            
            # Inject CSS
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        else:
            st.error(f"Theme file not found: {css_file}")
    except Exception as e:
        st.error(f"Failed to apply theme CSS: {str(e)}")

def _apply_font_css(font: str, dyslexia_mode: bool):
    """Apply font-related CSS based on user preferences"""
    css_parts = []
    
    # Base font family
    if font == "dyslexia" or dyslexia_mode:
        css_parts.append("""
        @import url('https://fonts.googleapis.com/css2?family=OpenDyslexic:wght@400;700&display=swap');
        * {
            font-family: 'OpenDyslexic', sans-serif !important;
        }
        """)
    elif font == "large":
        css_parts.append("""
        * {
            font-size: 16px !important;
        }
        h1 { font-size: 2.5rem !important; }
        h2 { font-size: 2rem !important; }
        h3 { font-size: 1.75rem !important; }
        p, div { font-size: 18px !important; }
        """)
    
    # Additional accessibility improvements
    if dyslexia_mode:
        css_parts.append("""
        .dyslexia-friendly {
            letter-spacing: 0.05em;
            line-height: 1.8;
            word-spacing: 0.1em;
        }
        """)
    
    if css_parts:
        st.markdown(f"<style>{''.join(css_parts)}</style>", unsafe_allow_html=True)

def _configure_streamlit_theme(theme: str):
    """Configure Streamlit's built-in theme options"""
    if theme == "dark":
        st._config.set_option("theme.base", "dark")
        st._config.set_option("theme.primaryColor", "#FF4B4B")
        st._config.set_option("theme.backgroundColor", "#0E1117")
        st._config.set_option("theme.secondaryBackgroundColor", "#1E1E1E")
        st._config.set_option("theme.textColor", "#FAFAFA")
    elif theme == "light":
        st._config.set_option("theme.base", "light")
        st._config.set_option("theme.primaryColor", "#FF2B2B")
        st._config.set_option("theme.backgroundColor", "#FAFAFA")
        st._config.set_option("theme.secondaryBackgroundColor", "#F0F0F0")
        st._config.set_option("theme.textColor", "#0E1117")

def get_theme_css_variables(theme: str) -> dict:
    """Get CSS variables for a specific theme"""
    if theme == "dark":
        return {
            "--primary": "#FF4B4B",
            "--secondary": "#1E1E1E",
            "--bg": "#0E1117",
            "--text": "#FAFAFA",
            "--border": "#333333"
        }
    elif theme == "light":
        return {
            "--primary": "#FF2B2B",
            "--secondary": "#F0F0F0",
            "--bg": "#FAFAFA",
            "--text": "#0E1117",
            "--border": "#E0E0E0"
        }
    else:
        return get_theme_css_variables("dark")  # Default to dark

def inject_custom_css():
    """Inject custom CSS with theme variables"""
    theme = get_theme()
    css_vars = get_theme_css_variables(theme)
    
    css = f"""
    :root {{
        --primary: {css_vars['--primary']};
        --secondary: {css_vars['--secondary']};
        --bg: {css_vars['--bg']};
        --text: {css_vars['--text']};
        --border: {css_vars['--border']};
    }}
    
    .custom-primary {{ color: var(--primary); }}
    .custom-secondary {{ color: var(--secondary); }}
    .custom-bg {{ background-color: var(--bg); }}
    .custom-text {{ color: var(--text); }}
    .custom-border {{ border-color: var(--border); }}
    
    .theme-aware-card {{
        background-color: var(--secondary);
        border: 1px solid var(--border);
        color: var(--text);
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }}
    """
    
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
