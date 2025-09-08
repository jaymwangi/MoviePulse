"""
Centralized style management for MoviePulse
Handles theme loading, component styles, and hover effects
"""

import streamlit as st
from pathlib import Path

def inject_css(css_str: str):
    """Injects raw CSS into the Streamlit app.
    
    Args:
        css_str: Raw CSS string to inject into the app
        
    Example:
        inject_css('.my-class { color: var(--primary-color); }')
    """
    st.markdown(f"<style>{css_str}</style>", unsafe_allow_html=True)

def load_css(css_file: str) -> str:
    """Load CSS from file and return as string
    
    Args:
        css_file: Path to CSS file (relative to this module)
        
    Returns:
        str: CSS content as string
    """
    css_path = Path(__file__).parent / css_file
    try:
        return css_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        st.error(f"CSS file not found: {css_file}")
        return ""

def load_custom_css(theme: str) -> str:
    """Load theme-specific CSS file with error handling
    
    Args:
        theme: Name of the theme to load (e.g., 'light', 'dark')
        
    Returns:
        str: Contents of the CSS file or empty string if not found
    """
    css_dir = Path(__file__).parent
    css_file = css_dir / f"theme_{theme}.css"
    
    try:
        return css_file.read_text(encoding='utf-8')
    except FileNotFoundError:
        st.error(f"Missing CSS file for {theme} theme")
        return ""

def apply_hover_effects() -> str:
    """Returns CSS for hover effects that work with both themes
    
    Returns:
        str: CSS string containing hover effect styles
    """
    return """
    <style>
        /* Base hover effect */
        .hover-effect:hover {
            transform: scale(1.02);
            transition: transform 0.2s ease;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Calendar-specific hover */
        .calendar-cell:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        /* Movie tile hover */
        .movie-tile:hover {
            transform: scale(1.05);
            z-index: 10;
        }
        
        /* Smooth transitions for all hoverable elements */
        [class*='hover-'] {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
    </style>
    """

def inject_component_styles(component_type: str) -> None:
    """Modular CSS injection for specific components
    
    Args:
        component_type: Type of component to style (e.g., 'mood_chips', 'actor_page')
    """
    styles = {
        "mood_chips": """
        <style>
            .mood-chip {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 0.4rem 0.8rem;
                border-radius: 1.5rem;
                transition: all 0.2s ease;
                cursor: pointer;
                margin: 0.1rem;
                font-size: 0.85rem;
                line-height: 1;
                border: 1px solid var(--border);
                color: var(--text-secondary);
                background: var(--secondary-background);
            }
            .mood-chip.selected {
                border-color: var(--primary-color);
                background: var(--mood-color);
                color: var(--mood-text-color);
            }
            .mood-chip:hover {
                filter: brightness(0.9);
                transform: translateY(-1px);
            }
            .mood-chip.disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
        </style>
        """,
        
        "actor_page": """
        <style>
            .actor-header { margin-bottom: 2rem; }
            .actor-metadata {
                display: flex;
                gap: 1.5rem;
                margin-top: 1rem;
            }
            .actor-image {
                border-radius: 12px;
                box-shadow: var(--shadow-md);
                transition: transform 0.3s ease;
            }
            .actor-image:hover {
                transform: scale(1.02);
            }
            @media (max-width: 768px) {
                .actor-metadata { flex-direction: column; }
            }
        </style>
        """,
        
        "pulse_animation": """
        <style>
            .max-selected { animation: pulse 1.5s infinite; }
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(255,0,0,0.4); }
                70% { box-shadow: 0 0 0 10px rgba(255,0,0,0); }
                100% { box-shadow: 0 0 0 0 rgba(255,0,0,0); }
            }
        </style>
        """
    }
    
    if component_type in styles:
        st.markdown(styles[component_type], unsafe_allow_html=True)

def initialize_theme() -> None:
    """Initialize theme CSS and global styles
    
    Loads:
    1. Theme-specific CSS variables
    2. Global base styles
    3. Hover effects
    """
    theme = st.session_state.get("theme", "light")
    
    # Load theme CSS
    theme_css = load_custom_css(theme)
    if theme_css:
        st.markdown(f"<style>{theme_css}</style>", unsafe_allow_html=True)
    
    # Load global styles and hover effects
    st.markdown("""
    <style>
        :root {
            --mood-color: var(--primary-color);
            --mood-text-color: var(--text-on-primary);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --transition-base: 0.2s ease;
        }
        
        /* Global back button style */
        .stButton button.back-button {
            background: var(--secondary-background);
            border: 1px solid var(--border);
        }
    </style>
    """ + apply_hover_effects(), unsafe_allow_html=True)

def load_page_styles(page_type: str) -> None:
    """Convenience function to load all styles for specific page types
    
    Args:
        page_type: Type of page to load styles for ('actor', 'mood_calendar', etc.)
    """
    initialize_theme()
    
    if page_type == "actor":
        inject_component_styles("actor_page")
        inject_component_styles("pulse_animation")
    elif page_type == "mood_calendar":
        inject_component_styles("mood_chips")

# Make functions available when importing from package
__all__ = [
    'inject_css',
    'load_css',          # Added this new function
    'load_custom_css',
    'apply_hover_effects',
    'inject_component_styles',
    'initialize_theme',
    'load_page_styles'
]