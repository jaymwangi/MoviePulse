import streamlit as st
from typing import Optional

def MoodTag(
    label: str,
    emoji: Optional[str] = None,
    tooltip: Optional[str] = None,
    size: str = "medium",  # "small", "medium", "large"
    variant: str = "default",  # "default", "outline", "solid"
    interactive: bool = False,
    selected: bool = False,
    key: Optional[str] = None
):
    """
    A reusable mood/genre tag component with emoji and tooltip support.
    
    Parameters:
    -----------
    label : str
        The text label for the tag
    emoji : str, optional
        An emoji to display before the label
    tooltip : str, optional
        Tooltip text that appears on hover
    size : str, default "medium"
        Size variant: "small", "medium", or "large"
    variant : str, default "default"
        Style variant: "default", "outline", or "solid"
    interactive : bool, default False
        Whether the tag is clickable/interactive
    selected : bool, default False
        If interactive, whether the tag is in selected state
    key : str, optional
        Unique key for interactive state management
    """
    
    # Size classes
    size_classes = {
        "small": "mood-tag-small",
        "medium": "mood-tag-medium",
        "large": "mood-tag-large"
    }
    
    # Variant classes
    variant_classes = {
        "default": "mood-tag-default",
        "outline": "mood-tag-outline",
        "solid": "mood-tag-solid"
    }
    
    # State classes
    state_class = "mood-tag-selected" if selected else ""
    interactive_class = "mood-tag-interactive" if interactive else ""
    
    # Build CSS classes string
    css_classes = f"mood-tag {size_classes[size]} {variant_classes[variant]} {state_class} {interactive_class}"
    
    # Create the tag content
    tag_content = f"{emoji} {label}" if emoji else label
    
    # Create the tag with tooltip if provided
    if tooltip:
        st.markdown(
            f"""
            <div class="{css_classes.strip()}" title="{tooltip}">
                {tag_content}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="{css_classes.strip()}">
                {tag_content}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Handle interactive behavior
    if interactive and key:
        # For interactive tags, we need to track state
        if st.session_state.get(key, False) != selected:
            st.session_state[key] = selected
            
        # Return the state for callback handling if needed
        return st.session_state.get(key, False)
