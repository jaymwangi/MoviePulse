# media_assets/styles/main.py
import streamlit as st
from pathlib import Path

def load_custom_css(theme):
    """Load CSS based on theme selection"""
    if theme == "dark":
        css_file = "theme_dark.css"
    else:
        css_file = "theme_light.css"
    
    try:
        with open(f"media_assets/styles/{css_file}", "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def inject_css(style_type: str):
    """Modular CSS injection system for components"""
    if style_type == "mood_chips":
        st.markdown(f"""
        <style>
            .mood-chip {{
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
            }}
            .mood-chip.selected {{
                border-color: var(--primary-color);
                background: var(--mood-color);
                color: var(--mood-text-color);
            }}
            .mood-chip:hover {{
                filter: brightness(0.9);
                transform: translateY(-1px);
            }}
            .mood-chip.disabled {{
                opacity: 0.5;
                cursor: not-allowed;
            }}
            .mood-emoji {{
                font-size: 1.1rem;
            }}
            .tooltip-wrapper {{
                position: relative;
                display: inline-block;
            }}
            .tooltip {{
                visibility: hidden;
                width: 200px;
                background-color: var(--tooltip-bg);
                color: var(--tooltip-text);
                text-align: center;
                border-radius: 6px;
                padding: 5px;
                position: absolute;
                z-index: 1;
                bottom: 125%;
                left: 50%;
                margin-left: -100px;
                opacity: 0;
                transition: opacity 0.3s;
                font-size: 0.8rem;
            }}
            .tooltip-wrapper:hover .tooltip {{
                visibility: visible;
                opacity: 1;
            }}
        </style>
        """, unsafe_allow_html=True)
    elif style_type == "pulse_animation":
        st.markdown("""
        <style>
            .max-selected { 
                animation: pulse 1.5s infinite; 
            }
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(255,0,0,0.4); }
                70% { box-shadow: 0 0 0 10px rgba(255,0,0,0); }
                100% { box-shadow: 0 0 0 0 rgba(255,0,0,0); }
            }
        </style>
        """, unsafe_allow_html=True)

def initialize_theme():
    """Initialize theme CSS and component styles"""
    theme = st.session_state.get("theme", "light")
    custom_css = load_custom_css(theme)
    if custom_css:
        st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)
    
    # Inject base component styles that work with both themes
    st.markdown("""
    <style>
        :root {
            --mood-color: var(--primary-color);
            --mood-text-color: var(--text-on-primary);
            --tooltip-bg: var(--secondary-background);
            --tooltip-text: var(--text-color);
        }
    </style>
    """, unsafe_allow_html=True)