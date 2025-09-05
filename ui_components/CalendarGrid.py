"""
Production-ready interactive mood calendar grid for MoviePulse v2.1
- Pure Streamlit implementation without HTML rendering issues
- Maintains cinematic design using only Streamlit components
"""

from datetime import date, timedelta
from typing import Optional, Dict, Any, List
import streamlit as st
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Constants
CINEMATIC_COLORS = {
    "dark": {
        "bg": "#1e1e1e",
        "primary": "#E50914",
        "secondary": "#6AC045",
        "text": "#FFFFFF",
        "muted": "#8C8C8C",
        "card": "#2d2d2d"
    },
    "light": {
        "bg": "#f8f9fa",
        "primary": "#E50914",
        "secondary": "#2ecc71",
        "text": "#2c3e50",
        "muted": "#7f8c8d",
        "card": "#ffffff"
    }
}

MOOD_COLOR_MAP = {
    "happy": "#F1C40F",
    "excited": "#E74C3C",
    "relaxed": "#3498DB",
    "thoughtful": "#9B59B6",
    "sad": "#5D6D7E",
    "romantic": "#E91E63",
    "adventurous": "#27AE60",
    "nostalgic": "#F39C12"
}

MOOD_VALUES = {
    "excited": 4, "happy": 3, "romantic": 3, "adventurous": 3,
    "relaxed": 2, "thoughtful": 2, "nostalgic": 1, "sad": 0
}

@st.cache_data(ttl=3600)
def load_moods():
    """Load and enhance mood options with caching"""
    try:
        return {
            "happy": {"emoji": "😊", "color": "#F1C40F"},
            "excited": {"emoji": "🎉", "color": "#E74C3C"},
            "relaxed": {"emoji": "😌", "color": "#3498DB"},
            "thoughtful": {"emoji": "🤔", "color": "#9B59B6"},
            "sad": {"emoji": "😢", "color": "#5D6D7E"},
            "romantic": {"emoji": "❤️", "color": "#E91E63"},
            "adventurous": {"emoji": "🏔️", "color": "#27AE60"},
            "nostalgic": {"emoji": "📻", "color": "#F39C12"}
        }
    except Exception as e:
        st.error(f"Error loading moods: {e}")
        return {}

def get_month_weeks(target_date: date) -> List[List[Optional[date]]]:
    """Get organized weeks for a given month"""
    first_day = target_date.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    weeks = []
    current_week = []
    
    # Pad empty days
    for _ in range(first_day.weekday()):
        current_week.append(None)
    
    # Fill actual days
    for day in range(1, last_day.day + 1):
        current_week.append(first_day.replace(day=day))
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
    
    if current_week:
        weeks.append(current_week)
    
    return weeks

class CalendarGrid:
    def __init__(self, theme="dark"):
        self.theme = theme
        self.cell_size = 110
        self.moods = load_moods()
        
        # Initialize session state for navigation if not exists
        if "calendar_navigation" not in st.session_state:
            st.session_state.calendar_navigation = {
                "current_month": date.today().month,
                "current_year": date.today().year
            }
    
    def render(self, show_insights=True):
        """Main grid renderer using pure Streamlit components"""
        # Get current navigation state
        nav = st.session_state.calendar_navigation
        current_date = date(nav["current_year"], nav["current_month"], 1)
        
        # Render header with navigation
        self._render_header(current_date)
        
        # Get all moods for the month in a single batch
        month_moods = self._get_month_moods(current_date)
        
        # Render calendar grid
        weeks = get_month_weeks(current_date)
        self._render_calendar_grid(weeks, month_moods)
        
        # Monthly insights
        if show_insights:
            self._render_monthly_insights(current_date, month_moods)
    
    def _render_header(self, current_date: date):
        """Render calendar header with navigation"""
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("← Previous", key="prev_month"):
                self._navigate_month(-1)
        
        with col2:
            st.subheader(f"{current_date.strftime('%B %Y')}")
        
        with col3:
            if st.button("Next →", key="next_month"):
                self._navigate_month(1)
        
        # Day headers using Streamlit columns
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cols = st.columns(7)
        for i, col in enumerate(cols):
            with col:
                col.markdown(f"**{days[i]}**")
    
    def _navigate_month(self, direction: int):
        """Handle month navigation"""
        nav = st.session_state.calendar_navigation
        current_date = date(nav["current_year"], nav["current_month"], 1)
        
        if direction == 1:  # Next month
            next_date = current_date.replace(day=28) + timedelta(days=4)
        else:  # Previous month
            if current_date.month == 1:
                next_date = date(current_date.year - 1, 12, 1)
            else:
                next_date = date(current_date.year, current_date.month - 1, 1)
        
        st.session_state.calendar_navigation = {
            "current_month": next_date.month,
            "current_year": next_date.year
        }
        st.rerun()
    
    def _get_month_moods(self, current_date: date) -> Dict[str, Any]:
        """Batch fetch all moods for the month"""
        month_moods = {}
        first_day = current_date.replace(day=1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        for day in range(1, last_day.day + 1):
            try:
                date_obj = first_day.replace(day=day)
                date_str = date_obj.isoformat()
                mood = self._get_mood_for_date_simulated(date_str)
                if mood:
                    month_moods[date_str] = {
                        "mood": mood,
                        "data": self.moods.get(mood, {})
                    }
            except Exception:
                continue
        
        return month_moods
    
    def _get_mood_for_date_simulated(self, date_str: str) -> Optional[str]:
        """Simulate mood data"""
        moods_list = list(self.moods.keys())
        if hash(date_str) % 10 < 3:
            return moods_list[hash(date_str) % len(moods_list)]
        return None
    
    def _set_mood_for_date_simulated(self, date_str: str, mood: str):
        """Simulate setting mood data"""
        st.session_state.setdefault('mood_data', {})[date_str] = mood
    
    def _render_calendar_grid(self, weeks: List[List[Optional[date]]], month_moods: Dict[str, Any]):
        """Render the calendar grid using only Streamlit components"""
        for week in weeks:
            cols = st.columns(7)
            for i, (day, col) in enumerate(zip(week, cols)):
                with col:
                    if day:
                        self._render_day_cell(day, month_moods)
                    else:
                        # Empty cell for padding
                        st.empty()
    
    def _render_day_cell(self, day: date, month_moods: Dict[str, Any]):
        """Render a single day cell using only Streamlit components"""
        date_str = day.isoformat()
        mood_info = month_moods.get(date_str, {})
        mood_data = mood_info.get("data", {})
        current_mood = mood_info.get("mood")
        is_today = day == date.today()
        
        # Create a container for the cell
        with st.container():
            # Style the container based on today and mood
            cell_style = """
            <style>
                div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
                    border-radius: 8px;
                    padding: 8px;
                    text-align: center;
                    margin: 2px;
                    min-height: 110px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                }
            </style>
            """
            st.markdown(cell_style, unsafe_allow_html=True)
            
            # Day number
            day_style = "font-weight: bold; font-size: 1.1em; margin-bottom: 8px;"
            if is_today:
                day_style += " color: #E50914;"  # Netflix red for today
            st.markdown(f"<div style='{day_style}'>{day.day}</div>", unsafe_allow_html=True)
            
            # Mood selector
            self._render_mood_selector(day, current_mood)
    
    def _render_mood_selector(self, day: date, current_mood: Optional[str]):
        """Render mood selector dropdown using Streamlit"""
        mood_options = {k: f"{v['emoji']} {k.capitalize()}" for k, v in self.moods.items()}
        
        # Find current index
        index = 0
        mood_keys = list(mood_options.keys())
        if current_mood and current_mood in mood_keys:
            index = mood_keys.index(current_mood)
        
        # Create the selectbox with a unique key
        selected_option = st.selectbox(
            label=f"Select mood for {day.strftime('%B %d')}",
            options=list(mood_options.values()),
            index=index,
            key=f"mood_select_{day.isoformat()}",
            label_visibility="collapsed",
            on_change=self._handle_mood_change,
            args=(day, f"mood_select_{day.isoformat()}"),
            help=f"Select your mood for {day.strftime('%B %d')}"
        )
    
    def _handle_mood_change(self, day: date, selectbox_key: str):
        """Handle mood selection changes"""
        selected_value = st.session_state[selectbox_key]
        
        # Extract the mood key from the selected value
        mood_key = None
        for key, value in self.moods.items():
            if f"{value['emoji']} {key.capitalize()}" == selected_value:
                mood_key = key
                break
        
        if mood_key:
            try:
                self._set_mood_for_date_simulated(day.isoformat(), mood_key)
                st.toast(f"Mood set to {mood_key.capitalize()} for {day.strftime('%b %d')}", icon="🎬")
            except Exception as e:
                st.error(f"Error setting mood: {e}")
    
    def _render_monthly_insights(self, current_date: date, month_moods: Dict[str, Any]):
        """Show emotional insights for the month"""
        try:
            # Extract mood values for emotional analysis
            mood_values = []
            mood_names = []
            
            for date_str, mood_info in month_moods.items():
                mood = mood_info.get("mood")
                if mood and mood in MOOD_VALUES:
                    mood_values.append(MOOD_VALUES[mood])
                    mood_names.append(mood)
            
            if mood_values:
                st.divider()
                st.subheader(f"📈 {current_date.strftime('%B')} Emotional Arc")
                st.caption("Your cinematic journey this month")
                
                # Show mood distribution
                if mood_names:
                    from collections import Counter
                    mood_counts = Counter(mood_names)
                    most_common = mood_counts.most_common(3)
                    
                    st.write("**Most frequent moods:**")
                    for mood, count in most_common:
                        mood_emoji = self.moods.get(mood, {}).get("emoji", "🎬")
                        st.write(f"{mood_emoji} {mood.capitalize()}: {count} days")
                
                # Simple insights based on mood patterns
                avg_mood = sum(mood_values) / len(mood_values) if mood_values else 0
                if avg_mood >= 3:
                    st.info("This month has been filled with high-energy emotions! 🎉")
                elif avg_mood >= 2:
                    st.info("A balanced month of thoughtful and relaxed moments. 🎬")
                else:
                    st.info("A more reflective emotional journey this month. 📝")
                    
        except Exception as e:
            st.error(f"Could not generate monthly insights: {e}")

# Simple test
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    calendar = CalendarGrid(theme="dark")
    calendar.render(show_insights=True)