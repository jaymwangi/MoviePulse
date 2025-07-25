# -*- coding: utf-8 -*-
import streamlit as st
from typing import Dict, List, Optional, Tuple
import json
import os
from pathlib import Path

class BadgeProgress:
    """A reusable component to display badge progress with visual progress bars"""

    TIER_ORDER = {"gold": 0, "silver": 1, "bronze": 2}  # Tier sort priority

    def __init__(self, user_id: str, badges_file: str = "static_data/cinephile_badges.json"):
        """
        Initialize the BadgeProgress component.
        
        Args:
            user_id: Unique identifier for the user
            badges_file: Path to the JSON file containing badge definitions
        """
        self.user_id = user_id
        self.badges_file = badges_file
        self.badge_data = self._load_badge_data()

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
        show_locked: bool = True
    ) -> None:
        """
        Display all badges with progress bars based on user stats.

        Args:
            user_stats: Dictionary of user statistics
            filter_tier: Optional tier to filter by ("bronze", "silver", "gold")
            columns_per_row: Number of badges to display per row
            show_locked: Whether to show locked badges or only unlocked ones
        """
        if not self.badge_data.get("badges"):
            st.warning("No badge data available")
            return

        badges = self._filter_and_sort_badges(user_stats, filter_tier, show_locked)

        if not badges:
            st.info(f"No {filter_tier if filter_tier else ''} badges available")
            return

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

        with st.container():
            # Badge header
            st.markdown(
                f"""
                <div style="border-left: 4px solid {tier_color}; padding-left: 1rem;">
                    <h4 style="margin-bottom: 0.2rem;">
                        {badge.get('icon', '')} {badge.get('name', '')}
                    </h4>
                    <p style="color: {tier_color}; margin-top: 0;">{tier} Tier</p>
                </div>
                """,
                unsafe_allow_html=True
            )

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
