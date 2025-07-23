# ui_components/MoodChip.py
import streamlit as st
from typing import Optional, Dict, List, Tuple, Callable
from functools import wraps
import time
import json
from pathlib import Path
from colorsys import rgb_to_hls, hls_to_rgb
import sys

# Add project root to path for module imports
sys.path.append(str(Path(__file__).parent.parent))

from media_assets.styles.main import inject_css

class MoodManager:
    """Centralized manager for mood configuration with enhanced caching."""
    
    _MOOD_DATA_PATH = Path(__file__).parent.parent / "static_data" / "mood_genre_mappings.json"
    _CACHE_TTL = 3600  # 1 hour cache

    @classmethod
    @st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
    def _load_mood_data(_cls) -> Dict:
        """Load and cache mood data from JSON file."""
        try:
            with open(_cls._MOOD_DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading mood data: {str(e)}")
            return _cls._get_fallback_data()

    @classmethod
    @st.cache_data(ttl=_CACHE_TTL)
    def get_mood_config(_cls) -> Dict:
        """Get complete cached mood configuration."""
        raw_data = _cls._load_mood_data()
        return {
            mood: {
                **data,
                "emoji": _cls._get_mood_emoji(mood),
                "color": _cls._get_mood_color(mood),
                "hover_color": _cls._get_hover_color(mood),
                "text_color": _cls._get_text_color(mood)
            }
            for mood, data in raw_data.items()
        }

    @classmethod
    def _get_mood_emoji(cls, mood: str) -> str:
        """Get emoji for specified mood."""
        emoji_map = {
            "Uplifting": "✨", "Melancholic": "☔", "Exciting": "⚡",
            "Romantic": "💖", "Chill": "🍃", "Suspenseful": "🔍",
            "Dark": "🖤", "Empowering": "💪", "Whimsical": "🎠",
            "Thought-Provoking": "🧠", "Cozy": "🛋️", "Eerie": "👻",
            "Reflective": "🤔", "Adventurous": "🗺️", "Nostalgic": "📻",
            "Mind-Bending": "🌀", "Heartwarming": "🥰", "Gritty": "🏙️"
        }
        return emoji_map.get(mood, "❓")

    @classmethod
    def _get_mood_color(cls, mood: str) -> str:
        """Generate base color for mood."""
        color_map = {
            "Uplifting": "#FFD700", "Melancholic": "#A7C7E7",
            "Exciting": "#FFA500", "Romantic": "#FFB6C1",
            "Chill": "#98FB98", "Suspenseful": "#D3D3D3",
            "Dark": "#696969", "Empowering": "#9370DB",
            "Whimsical": "#BA55D3", "Thought-Provoking": "#20B2AA",
            "Cozy": "#D2B48C", "Eerie": "#708090",
            "Reflective": "#6495ED", "Adventurous": "#3CB371",
            "Nostalgic": "#FFA07A", "Mind-Bending": "#9ACD32",
            "Heartwarming": "#FF6347", "Gritty": "#778899"
        }
        return color_map.get(mood, "#F5F5F5")

    @classmethod
    def _get_text_color(cls, mood: str) -> str:
        """Determine optimal text color based on background brightness."""
        bg_color = cls._get_mood_color(mood)
        if bg_color.startswith("#"):
            r, g, b = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return "#FFFFFF" if brightness < 128 else "#000000"
        return "#000000"

    @classmethod
    def _get_hover_color(cls, mood: str) -> str:
        """Generate hover color by adjusting base color lightness."""
        base_color = cls._get_mood_color(mood)
        if base_color.startswith("#"):
            try:
                r, g, b = tuple(int(base_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                h, l, s = rgb_to_hls(r/255, g/255, b/255)
                new_l = min(1.0, l * 1.3)  # Lighten by 30%
                nr, ng, nb = hls_to_rgb(h, new_l, s)
                return f"#{int(nr*255):02x}{int(ng*255):02x}{int(nb*255):02x}"
            except:
                return "#EEEEEE"
        return "#EEEEEE"

    @classmethod
    def _get_fallback_data(cls) -> Dict:
        """Provide fallback data if JSON loading fails."""
        return {
            "Uplifting": {
                "genres": [35, 10751, 10402],
                "weight": 1.2,
                "description": "Feel-good films to boost your mood",
                "conflicts": ["Melancholic", "Dark"]
            },
            "Melancholic": {
                "genres": [18, 36, 10749],
                "weight": 1.0,
                "description": "Bittersweet, reflective stories",
                "conflicts": ["Uplifting", "Exciting"]
            }
        }

    @classmethod
    def get_available_moods(_cls) -> List[str]:
        """Return cached list of available mood names."""
        return list(_cls.get_mood_config().keys())

    @classmethod
    def get_moods_by_genre(_cls, genre_id: int) -> List[str]:
        """Get all moods associated with a specific genre ID."""
        return [
            mood for mood, config in _cls.get_mood_config().items()
            if genre_id in config.get("genres", [])
        ]

    @classmethod
    def get_compatible_moods(_cls, selected_moods: List[str]) -> List[str]:
        """Get moods that are compatible with current selections."""
        all_moods = _cls.get_available_moods()
        if not selected_moods:
            return all_moods
        
        mood_config = _cls.get_mood_config()
        return [
            mood for mood in all_moods
            if not set(mood_config[mood].get("conflicts", [])) & set(selected_moods)
        ]

def validate_moods(func: Callable) -> Callable:
    """Decorator to validate mood lists against available moods."""
    @wraps(func)
    def wrapper(moods: List[str], *args, **kwargs):
        available = MoodManager.get_available_moods()
        invalid = set(moods) - set(available)
        if invalid:
            examples = ", ".join(available[:3])
            raise ValueError(
                f"Invalid moods: {invalid}. "
                f"First 3 valid options: {examples} (total {len(available)} available)"
            )
        return func(moods, *args, **kwargs)
    return wrapper

def MoodChip(
    mood: str,
    default: bool = False,
    key: Optional[str] = None,
    disabled: bool = False,
    compact: bool = True,
    show_tooltip: bool = True,
    in_sidebar: bool = True
) -> bool:
    """Optimized mood chip component for sidebar usage."""
    try:
        config = MoodManager.get_mood_config()[mood]
    except KeyError as e:
        raise ValueError(str(e)) from e

    component_key = f"moodchip_{key if key else mood}"
    
    # Initialize session state
    if component_key not in st.session_state:
        st.session_state[component_key] = default

    # Inject CSS styles
    inject_css("mood_chips")
    
    # Generate dynamic CSS variables
    st.markdown(f"""
    <style>
        :root {{
            --mood-color: {config['color']};
            --mood-hover-color: {config['hover_color']};
            --mood-text-color: {config['text_color']};
        }}
    </style>
    """, unsafe_allow_html=True)

    # Create the chip element
    container = st.sidebar.container() if in_sidebar else st.container()
    clicked = False
    
    with container:
        if in_sidebar and compact:
            # Optimized sidebar compact version
            cols = st.columns([1, 4])
            with cols[0]:
                st.markdown(f"<div class='mood-emoji'>{config['emoji']}</div>", unsafe_allow_html=True)
            with cols[1]:
                clicked = st.checkbox(
                    mood,
                    value=st.session_state[component_key],
                    key=f"{component_key}_cb",
                    disabled=disabled,
                    label_visibility="visible"
                )
        else:
            # Enhanced version with tooltips
            display_text = "" if compact else mood
            tooltip = f"<span class='tooltip'>{config['description']}</span>" if show_tooltip else ""
            
            st.markdown(
                f"""
                <div class="tooltip-wrapper">
                    <div role="button" 
                         aria-pressed={'true' if st.session_state[component_key] else 'false'}
                         aria-label="{mood} mood filter"
                         class="mood-chip {'selected' if st.session_state[component_key] else ''} {'disabled' if disabled else ''}"
                         onclick="this.nextElementSibling.click()">
                        <span class="mood-emoji">{config['emoji']}</span>
                        {display_text}
                    </div>
                    {tooltip}
                </div>
                """,
                unsafe_allow_html=True
            )
            
            clicked = st.button(
                f"Toggle {mood}",
                key=f"{component_key}_btn",
                disabled=disabled,
                label_visibility="collapsed"
            )

    # Update state if clicked
    if clicked and not disabled:
        st.session_state[component_key] = not st.session_state[component_key]
        st.rerun()
    
    return st.session_state[component_key]
@validate_moods
def MoodSelector(
    moods: Optional[List[str]] = None,
    max_selections: int = 3,
    cols: int = 2,  # Changed to ensure this is always an integer
    key: str = "mood_selector",
    in_sidebar: bool = True,
    show_counter: bool = True
) -> List[str]:
    """Sidebar-optimized mood selector with selection limits."""
    available_moods = MoodManager.get_available_moods()
    moods_to_show = moods or available_moods
    
    # Initialize selection tracking
    selection_key = f"{key}_selections"
    if selection_key not in st.session_state:
        st.session_state[selection_key] = []
    
    current_selections = st.session_state[selection_key]
    
    # Create grid layout
    container = st.sidebar if in_sidebar else st
    with container:
        if show_counter:
            counter_col, _ = st.columns([1, 3])
            with counter_col:
                st.caption(f"{len(current_selections)}/{max_selections if max_selections > 0 else '∞'} selected")
        
        if max_selections and len(current_selections) >= max_selections:
            inject_css("pulse_animation")
        
        # Ensure cols is an integer
        num_columns = int(cols) if isinstance(cols, (int, float)) else 2
        
        for i in range(0, len(moods_to_show), num_columns):
            columns = st.columns(num_columns)  # Use the validated number of columns
            for col_idx, col in enumerate(columns):
                mood_idx = i + col_idx
                if mood_idx < len(moods_to_show):
                    mood = moods_to_show[mood_idx]
                    with col:
                        selected = MoodChip(
                            mood,
                            default=mood in current_selections,
                            key=f"{key}_{mood}",
                            disabled=(
                                max_selections > 0 and 
                                len(current_selections) >= max_selections and 
                                mood not in current_selections
                            ),
                            compact=True,
                            in_sidebar=in_sidebar
                        )
                        
                        # Update selections
                        if selected and mood not in current_selections:
                            st.session_state[selection_key].append(mood)
                            st.rerun()
                        elif not selected and mood in current_selections:
                            st.session_state[selection_key].remove(mood)
                            st.rerun()
    
    return st.session_state[selection_key]

def clear_mood_selections(key: str = "mood_selector"):
    """Clear all mood selections for a given key."""
    selection_key = f"{key}_selections"
    if selection_key in st.session_state:
        del st.session_state[selection_key]
    st.rerun()

def save_mood_preferences(user_id: str, selections: List[str]):
    """Save mood preferences to user profile."""
    from session_utils.user_profile import update_user_profile
    update_user_profile(user_id, {"mood_preferences": selections})

def load_mood_preferences(user_id: str) -> List[str]:
    """Load mood preferences from user profile."""
    from session_utils.user_profile import get_user_profile
    profile = get_user_profile(user_id)
    return profile.get("mood_preferences", [])
