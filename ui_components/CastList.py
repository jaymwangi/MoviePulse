"""
Enhanced Cast List Component with Actor Navigation
-------------------------------------------------
Features:
- Clickable actor cards that navigate to actor profiles
- Responsive grid layout
- Profile image placeholders
- Character role display
"""

import streamlit as st
from typing import List
from core_config.constants import Person

class CastList:
    @staticmethod
    def display(cast: List[Person], columns: int = 6, max_rows: int = 2):
        """
        Display clickable cast members in a responsive grid
        
        Args:
            cast: List of Person objects with id, name, character, profile_path
            columns: Number of columns in grid
            max_rows: Maximum rows to display
        """
        if not cast:
            st.warning("No cast information available")
            return
        
        st.subheader("Cast")
        cols = st.columns(min(columns, len(cast) or 1))  # Handle empty cast
        
        for idx, person in enumerate(cast[:columns*max_rows]):
            with cols[idx % columns]:
                # Create a clickable container for each cast member
                clicked = st.button(
                    key=f"cast_{person.id}_{idx}",
                    label="",  # Empty label since we're using image as the button
                    help=f"Click to view {person.name}'s profile"
                )
                
                if clicked:
                    # Update session state and trigger navigation
                    st.session_state["current_actor"] = {
                        "id": person.id,
                        "name": person.name,
                        "profile_path": person.profile_path
                    }
                    st.session_state["current_page"] = "page_05_actor_profile"
                    st.rerun()
                
                # Profile image with error handling
                try:
                    img_url = f"https://image.tmdb.org/t/p/w185{person.profile_path}"
                    st.image(
                        img_url,
                        width=100,
                        caption=person.name,
                        use_column_width=True
                    )
                except:
                    st.image(
                        "media_assets/icons/person_placeholder.png",
                        width=100,
                        caption=person.name
                    )
                
                # Character name with ellipsis for long roles
                if person.role:
                    role = (person.role[:15] + '...') if len(person.role) > 18 else person.role
                    st.caption(f"as {role}", help=person.role if len(person.role) > 18 else None)

# Create alias for backward compatibility
display = CastList.display