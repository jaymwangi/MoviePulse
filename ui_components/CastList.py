import streamlit as st
from typing import List
from core_config.constants import Person

def display(cast: List[Person], columns: int = 6, max_rows: int = 2):
    """
    Enhanced version with:
    - Responsive column count
    - Max row limitation
    - Better error handling
    """
    if not cast:
        st.warning("No cast information available")
        return
    
    st.subheader("Cast")
    cols = st.columns(min(columns, len(cast) or 1))  # Handle empty cast
    
    for idx, person in enumerate(cast[:columns*max_rows]):
        with cols[idx % columns]:
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