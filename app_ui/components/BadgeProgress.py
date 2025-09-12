# app_ui/components/BadgeDisplay.py

import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from media_assets.styles.components import badge_styles

class BadgeProgress:
    """A reusable component to display badge progress with visual progress bars"""
    
    # Tier order for sorting
    TIER_ORDER = {"gold": 0, "silver": 1, "bronze": 2}

    def __init__(self, user_id: str = "default_user", badges_file: str = "static_data/cinephile_badges.json"):
        """
        Initialize the BadgeDisplay component.
        
        Args:
            user_id: Unique identifier for the user
            badges_file: Path to the JSON file containing badge definitions
        """
        self.user_id = user_id
        self.badges_file = badges_file
        self.badge_data = self._load_badge_data()
        self.styles = badge_styles()

    def _load_badge_data(self) -> Dict:
        """Load badge definitions from JSON file with enhanced error handling"""
        try:
            abs_path = Path(self.badges_file).absolute()
            if not os.path.exists(abs_path):
                raise FileNotFoundError(f"File not found at: {abs_path}")

            with open(abs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate basic structure
            if not isinstance(data.get("badges"), list):
                raise ValueError("Badge data must contain a 'badges' list")

            return data

        except FileNotFoundError:
            st.error(f"⚠️ Badge configuration not found at: {self.badges_file}")
            return {"badges": [], "tracking_fields": {}}
        except json.JSONDecodeError:
            st.error("⚠️ Invalid badge configuration format")
            return {"badges": [], "tracking_fields": {}}
        except Exception as e:
            st.error(f"⚠️ Error loading badges: {str(e)}")
            return {"badges": [], "tracking_fields": {}}

    def _get_tier_color(self, tier: str) -> str:
        """Get color based on badge tier with theme awareness"""
        colors = {
            "bronze": "#cd7f32",  # bronze color
            "silver": "#c0c0c0",  # silver color
            "gold": "#ffd700",    # gold color
        }
        return colors.get(tier.lower(), "#6c757d")  # default to gray

    def display_badge_progress(
        self,
        user_stats: Dict[str, int],
        filter_tier: Optional[str] = None,
        columns_per_row: int = 3,
        show_locked: bool = True,
        title: str = "Your Badge Progress"
    ) -> None:
        """
        Display all badges with progress bars based on user stats.

        Args:
            user_stats: Dictionary of user statistics
            filter_tier: Optional tier to filter by ("bronze", "silver", "gold")
            columns_per_row: Number of badges to display per row
            show_locked: Whether to show locked badges or only unlocked ones
            title: Section title
        """
        if not self.badge_data.get("badges"):
            st.warning("No badge data available")
            return

        badges = self._filter_and_sort_badges(user_stats, filter_tier, show_locked)

        if not badges:
            st.info(f"No {filter_tier if filter_tier else ''} badges available")
            return

        # Display title
        st.subheader(title)
        
        # Apply styles
        st.markdown(self.styles, unsafe_allow_html=True)

        # Create responsive columns
        cols = st.columns(columns_per_row)

        for idx, badge in enumerate(badges):
            with cols[idx % columns_per_row]:
                self._display_single_badge(badge, user_stats)

    def _filter_and_sort_badges(
        self,
        user_stats: Dict[str, int],
        filter_tier: Optional[str],
        show_locked: bool
    ) -> List[Dict]:
        """Filter and sort badges based on criteria"""
        badges = self.badge_data["badges"]

        # Apply tier filter
        if filter_tier:
            badges = [b for b in badges if b.get("tier", "").lower() == filter_tier.lower()]

        processed_badges = []
        for badge in badges:
            tracking_field = badge.get("tracking_field")
            current = user_stats.get(tracking_field, 0)
            threshold = badge.get("threshold", 1)
            progress = min(current / threshold * 100, 100)
            unlocked = current >= threshold

            if show_locked or unlocked:
                processed_badges.append({
                    **badge,
                    "current": current,
                    "progress": progress,
                    "unlocked": unlocked
                })

        return sorted(
            processed_badges,
            key=lambda x: (
                not x["unlocked"],
                self.TIER_ORDER.get(x.get("tier", "").lower(), 3),
                -x["progress"]
            )
        )

    def _display_single_badge(self, badge: Dict, user_stats: Dict[str, int]) -> None:
        """Display a single badge with progress information"""
        tier = badge.get("tier", "").capitalize()
        tier_color = self._get_tier_color(badge.get("tier", ""))
        current = badge["current"]
        threshold = badge["threshold"]
        progress = badge["progress"]
        unlocked = badge["unlocked"]

        # Use badge container styling
        badge_class = "badge medium"
        if not unlocked:
            badge_class += " locked"

        badge_html = f"""
        <div class="{badge_class}">
            <div style="border-left: 4px solid {tier_color}; padding-left: 1rem;">
                <div class="badge-icon">{badge.get('icon', '🏆')}</div>
                <div class="badge-name">{badge.get('name', '')}</div>
                <div style="color: {tier_color}; margin-top: 0.2rem;">{tier} Tier</div>
            </div>
        </div>
        """

        st.markdown(badge_html, unsafe_allow_html=True)
        
        # Progress bar
        st.progress(int(progress))
        st.caption(f"{current}/{threshold} ({progress:.0f}%)")

        # Description
        st.markdown(f"*{badge.get('description', '')}*")

        # Unlock status
        if unlocked:
            st.success(f"✓ {badge.get('unlock_message', 'Unlocked!')}")
        else:
            remaining = threshold - current
            st.info(f"🔒 {remaining} more to unlock")

        st.divider()

    def render_badge_grid(self, user_stats: Dict[str, int], columns: int = 3, title: str = "Your Badges"):
        """
        Render a grid of badges in a more compact format.
        
        Args:
            user_stats: Dictionary of user statistics
            columns: Number of columns in the grid
            title: Section title
        """
        if not self.badge_data.get("badges"):
            return

        st.subheader(title)
        st.markdown(self.styles, unsafe_allow_html=True)

        # Create CSS grid
        grid_html = f"""
        <div class="badge-grid" style="display: grid; grid-template-columns: repeat({columns}, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
        """

        for badge in self.badge_data["badges"]:
            tracking_field = badge.get("tracking_field")
            current = user_stats.get(tracking_field, 0)
            threshold = badge.get("threshold", 1)
            unlocked = current >= threshold
            tier_color = self._get_tier_color(badge.get("tier", ""))

            badge_class = "badge small"
            if not unlocked:
                badge_class += " locked"

            grid_html += f"""
            <div class="{badge_class}" title="{badge.get('description', '')}">
                <span class="badge-icon">{badge.get('icon', '🏆')}</span>
                <span class="badge-name">{badge.get('name', '')}</span>
                {f'<span class="badge-progress">{current}/{threshold}</span>' if not unlocked else ''}
            </div>
            """

        grid_html += "</div>"
        st.markdown(grid_html, unsafe_allow_html=True)

    def render_achievement_summary(self, user_stats: Dict[str, int]):
        """Render a summary of achievement progress"""
        if not self.badge_data.get("badges"):
            return

        total_badges = len(self.badge_data["badges"])
        unlocked_badges = sum(
            1 for badge in self.badge_data["badges"]
            if user_stats.get(badge.get("tracking_field", ""), 0) >= badge.get("threshold", 1)
        )

        st.subheader("Achievement Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Badges", total_badges)
        with col2:
            st.metric("Unlocked", unlocked_badges)
        with col3:
            progress = (unlocked_badges / total_badges * 100) if total_badges > 0 else 0
            st.metric("Completion", f"{progress:.1f}%")

    def get_user_badge_summary(self, user_stats: Dict[str, int]) -> Dict[str, Tuple[int, int, bool]]:
        """Get summary of badge progress for the user"""
        summary = {}
        for badge in self.badge_data.get("badges", []):
            tracking_field = badge.get("tracking_field")
            if tracking_field:
                current = user_stats.get(tracking_field, 0)
                threshold = badge.get("threshold", 1)
                summary[badge["id"]] = (current, threshold, current >= threshold)
        return summary

    def get_tracking_fields(self) -> Dict[str, Dict]:
        """Get all tracking field definitions"""
        return self.badge_data.get("tracking_fields", {})