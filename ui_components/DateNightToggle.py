# -*- coding: utf-8 -*-
import streamlit as st
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
from uuid import uuid4
from session_utils.state_tracker import initiate_date_night

def load_starter_packs() -> Dict[str, Dict]:
    """Load starter packs from JSON file with enhanced error handling"""
    packs_path = Path(__file__).parent.parent / "static_data" / "starter_packs.json"
    try:
        with open(packs_path, "r", encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data.get("packs"), dict):
                st.error("Invalid starter packs format: expected dictionary")
                return {}
            return data["packs"]
    except FileNotFoundError:
        st.error("Starter packs file not found")
        return {}
    except json.JSONDecodeError:
        st.error("Invalid JSON in starter packs file")
        return {}
    except Exception as e:
        st.error(f"Unexpected error loading packs: {str(e)}")
        return {}

def _get_pack_icon(pack_type: Optional[str]) -> str:
    """Get appropriate icon for pack type"""
    icons = {
        "romance": "💖",
        "adventure": "🏔️",
        "comedy": "😂",
        "horror": "👻",
        "scifi": "🚀",
        None: "🎬"
    }
    return icons.get(pack_type, "🎭")

def display_pack_summary(pack: Dict[str, Any]):
    """Display summary for your pack structure"""
    if not pack:
        st.warning("No pack data available")
        return
    
    name = pack.get("name", "Unnamed Pack")
    st.markdown(f"#### {name}")
    
    cols = st.columns(2)
    with cols[0]:
        st.write("**Movies**")
        st.caption(f"{len(pack.get('movies', []))} selected movies")
        
    with cols[1]:
        st.write("**Moods**")
        for mood, score in pack.get("moods", {}).items():
            st.progress(score, text=f"{mood.replace('-', ' ').title()} ({score:.0%})")
    
    if pack.get("compatible_with"):
        st.write("**Works well with:**")
        st.caption(", ".join(pack["compatible_with"]))
        
def display_date_night_toggle():
    """Enhanced Date Night UI with validation and rich feedback"""
    st.subheader("🌹 Date Night Mode")
    st.caption("Combine preferences with a partner for shared recommendations")
    
    packs = load_starter_packs()
    if not packs:
        st.warning("No valid starter packs available")
        return
    
    # Filter out invalid packs
    valid_packs = {
        name: pack for name, pack in packs.items()
        if all(k in pack for k in ["name", "genres", "moods"])
        and isinstance(pack["genres"], list)
        and isinstance(pack["moods"], dict)
    }
    
    if not valid_packs:
        st.error("No valid packs available - check pack definitions")
        return
    
    pack_names = sorted(valid_packs.keys())
    
    with st.container(border=True):
        cols = st.columns(2)
        with cols[0]:
            pack_a_name = st.selectbox(
                "Your Pack",
                options=pack_names,
                key="pack_a_select",
                index=None,
                placeholder="Choose your pack...",
                help="Select your preferred starter pack",
                label_visibility="collapsed"
            )
        with cols[1]:
            pack_b_name = st.selectbox(
                "Partner's Pack",
                options=pack_names,
                key="pack_b_select",
                index=None,
                placeholder="Choose their pack...",
                help="Select your partner's starter pack",
                label_visibility="collapsed"
            )
    
    # Display selected packs
    if pack_a_name and pack_b_name:
        pack_a = valid_packs[pack_a_name]
        pack_b = valid_packs[pack_b_name]
        
        st.divider()
        cols = st.columns(2)
        with cols[0]:
            with st.expander(f"🧑 Your Pack: {pack_a['name']}", expanded=True):
                display_pack_summary(pack_a)
        with cols[1]:
            with st.expander(f"🧑 Partner's Pack: {pack_b['name']}", expanded=True):
                display_pack_summary(pack_b)
        
        # Action buttons
        cols = st.columns([3, 1])
        with cols[0]:
            if st.button(
                "✨ Activate Date Night",
                type="primary",
                use_container_width=True,
                help="Combine these packs for shared recommendations"
            ):
                try:
                    initiate_date_night(pack_a, pack_b)
                    st.rerun()
                except Exception as e:
                    st.error(f"Activation failed: {str(e)}")
        with cols[1]:
            if st.button(
                "Clear",
                use_container_width=True,
                help="Reset selections"
            ):
                for key in ["pack_a_select", "pack_b_select"]:
                    st.session_state.pop(key, None)
                st.rerun()

def show_date_night_status():
    """Display current Date Night status badge with end option"""
    if st.session_state.get("date_night_active"):
        pack_a = st.session_state.get("original_packs", {}).get("pack_a", {}).get("name", "Unknown")
        pack_b = st.session_state.get("original_packs", {}).get("pack_b", {}).get("name", "Unknown")
        
        with st.sidebar:
            st.markdown(
                f"""
                <div style="border-radius: 0.5rem; padding: 0.5rem; background-color: #FF4B4B20; 
                            border: 1px solid #FF4B4B; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: bold; color: #FF4B4B;">❤️ Date Night Active</div>
                            <div style="font-size: 0.8rem; color: #666;">
                                {pack_a} + {pack_b}
                            </div>
                        </div>
                        <div>
                            <button onclick="endDateNight()" style="
                                background: none; 
                                border: none; 
                                color: #FF4B4B; 
                                cursor: pointer;
                                font-size: 1.2rem;
                                padding: 0 0.5rem;
                            ">✕</button>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # JavaScript to handle the end date night button
            st.markdown("""
            <script>
            function endDateNight() {
                fetch('/_end_date_night', {
                    method: 'POST'
                }).then(() => window.location.reload());
            }
            </script>
            """, unsafe_allow_html=True)

# Test the component when run directly
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("🎬 Date Night Mode Tester")
    
    display_date_night_toggle()
    show_date_night_status()
    
    if st.session_state.get("date_night_active"):
        st.success("Date Night mode is active!")
        st.json({
            "pack_a": st.session_state.pack_a,
            "pack_b": st.session_state.pack_b
        })