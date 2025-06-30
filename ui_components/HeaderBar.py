# ui_components/HeaderBar.py
import streamlit as st
from session_utils.state_tracker import (
    toggle_theme,
    get_current_theme,
    sync_theme_to_config
)

def render_app_header():
    """
    Clean header component containing only:
    - Branding/logo
    - Theme toggle
    - Navigation elements (no search)
    """
    # Ensure theme is synced (critical for first load)
    sync_theme_to_config()
    
    # ---- 1. HEADER CONTAINER ----
    with st.container():
        # Responsive CSS grid
        st.markdown("""
        <style>
            .header-grid {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: center;
                gap: 1rem;
                background: linear-gradient(90deg, var(--header-dark) 0%, var(--header-darker) 100%);
                padding: 1rem;
                border-radius: 0 0 10px 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                margin-bottom: 2rem;
            }
            
            @media (max-width: 768px) {
                .header-grid {
                    grid-template-columns: 1fr;
                }
            }
            
            :root {
                --header-dark: #0a0a0a;
                --header-darker: #1a1a2e;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # ---- 2. HEADER GRID ----
        st.markdown('<div class="header-grid">', unsafe_allow_html=True)
        
        # Left Column - Branding
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 15px; min-width: 0;">
            <img src="media_assets/logos/moviepulse_{'dark' if get_current_theme() == 'dark' else 'light'}.png" 
                 width="400" 
                 style="max-width: 100%; height: auto;">
            <p style="font-size: 0.9rem; opacity: 0.8; margin: 0; white-space: nowrap;">
                Your <span style="color: #FF4B4B;">cinematic universe</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Right Column - Theme Toggle Only
        with st.container():
            st.button(
                f"{'🌙' if get_current_theme() == 'dark' else '☀️'}",
                on_click=toggle_theme,
                help="Toggle light/dark mode",
                use_container_width=True,
                key="header_theme_toggle"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)