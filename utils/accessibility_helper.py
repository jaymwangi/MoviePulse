import streamlit as st
from session_utils.user_profile import load_user_preferences

def apply_accessibility_settings():
    """Apply accessibility settings to the current page"""
    prefs = load_user_preferences()
    
    # Apply dyslexia-friendly mode
    if prefs.get("dyslexia_mode", False):
        st.markdown("""
        <style>
            @import url('https://cdn.jsdelivr.net/npm/open-dyslexic@1.0.3/webfont.css');
            
            * {
                font-family: OpenDyslexic, sans-serif !important;
                letter-spacing: 0.05em;
                line-height: 1.8;
                word-spacing: 0.1em;
            }
        </style>
        """, unsafe_allow_html=True)
    
    # Apply high contrast mode
    if prefs.get("high_contrast", False):
        st.markdown("""
        <style>
            :root {
                --primary: #000000;
                --secondary: #333333;
            }
            
            .stButton > button {
                background-color: #000000;
                color: #FFFFFF;
                border: 2px solid #000000;
            }
            
            .stSelectbox, .stTextInput, .stTextArea {
                background-color: #FFFFFF;
                color: #000000;
            }
        </style>
        """, unsafe_allow_html=True)
    
    # Note: Spoiler-free mode is handled in content rendering components
