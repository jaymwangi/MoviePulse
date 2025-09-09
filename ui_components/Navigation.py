# ui_components/Navigation.py
import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Import the analytics client (make sure this exists from Task 1)
try:
    from service_clients.analytics_client import AnalyticsClient
except ImportError:
    # Fallback if analytics client is not available
    class AnalyticsClient:
        @staticmethod
        def log_event(event_type, **kwargs):
            logger.warning(f"Analytics event (fallback): {event_type} - {kwargs}")

def back_button(
    target_page: str,
    label: str = "← Back",
    key: Optional[str] = None,
    use_session_state: bool = True,
    **button_kwargs
):
    """
    Creates a consistent back button that navigates to a specified page.
    
    Args:
        target_page (str): The page name to navigate back to (e.g., "Home")
        label (str): Button label (defaults to ← Back)
        key (str, optional): Unique key for Streamlit button
        use_session_state (bool): If True, uses session_state for navigation
        **button_kwargs: Additional styling arguments for st.button
        
    Example:
        back_button("Home", label="Go Back", use_container_width=True)
    """
    default_kwargs = {
        "type": "secondary",
        "use_container_width": True,
    }
    
    # Merge default and user-provided kwargs
    final_kwargs = {**default_kwargs, **button_kwargs}
    
    if st.button(label, key=key, **final_kwargs):
        try:
            # Log navigation event
            AnalyticsClient.log_event(
                event_type="navigation",
                navigation_type="back_button",
                source_page=st.session_state.get('current_page', 'unknown'),
                target_page=target_page,
                timestamp=datetime.now().isoformat(),
                success=True
            )
        except Exception as e:
            logger.error(f"Error logging navigation: {e}")
            st.error(f"Error logging navigation: {e}")
        
        if use_session_state:
            st.session_state.current_page = target_page
        else:
            st.experimental_set_query_params(page=target_page)
        
        # Force a rerun to trigger the page change
        st.rerun()

def navigate_to_page(
    page_name: str,
    button_label: str = "Navigate",
    use_session_state: bool = True,
    **button_kwargs
):
    """
    Creates a navigation button to a specific page with analytics logging.
    
    Args:
        page_name (str): The target page name
        button_label (str): Button label text
        use_session_state (bool): Use session state for navigation
        **button_kwargs: Additional button styling arguments
    """
    if st.button(button_label, **button_kwargs):
        try:
            # Log navigation event
            AnalyticsClient.log_event(
                event_type="navigation",
                navigation_type="button_click",
                source_page=st.session_state.get('current_page', 'unknown'),
                target_page=page_name,
                timestamp=datetime.now().isoformat(),
                success=True
            )
        except Exception as e:
            logger.error(f"Error logging navigation: {e}")
            st.error(f"Error logging navigation: {e}")
        
        if use_session_state:
            st.session_state.current_page = page_name
            st.rerun()
        else:
            st.experimental_set_query_params(page=page_name)
            st.rerun()

def navigate_to_movie_details(movie_id: int, movie_title: str = "", source: str = "unknown"):
    """
    Navigates to movie details page with analytics logging and robust error handling.
    
    Args:
        movie_id (int): The TMDB movie ID
        movie_title (str): Movie title for logging purposes
        source (str): Source of the navigation (e.g., "poster_click", "button")
    """
    try:
        # Log navigation attempt
        AnalyticsClient.log_event(
            event_type="navigation_attempt",
            navigation_type="movie_details",
            source_page=st.session_state.get('current_page', 'unknown'),
            target_page="Movie Details",
            movie_id=movie_id,
            movie_title=movie_title,
            source=source,
            timestamp=datetime.now().isoformat(),
            success=False  # Will be updated if successful
        )
        
        # Set query parameters for movie details page
        st.query_params.update({"movie_id": movie_id})
        
        # Log successful navigation
        AnalyticsClient.log_event(
            event_type="navigation",
            navigation_type="movie_details",
            source_page=st.session_state.get('current_page', 'unknown'),
            target_page="Movie Details",
            movie_id=movie_id,
            movie_title=movie_title,
            source=source,
            timestamp=datetime.now().isoformat(),
            success=True
        )
        
        st.rerun()
        
    except Exception as e:
        error_msg = f"Failed to navigate to movie details: {str(e)}"
        logger.error(error_msg)
        
        # Log navigation failure
        try:
            AnalyticsClient.log_event(
                event_type="navigation_error",
                navigation_type="movie_details",
                source_page=st.session_state.get('current_page', 'unknown'),
                target_page="Movie Details",
                movie_id=movie_id,
                movie_title=movie_title,
                source=source,
                error=str(e),
                timestamp=datetime.now().isoformat(),
                success=False
            )
        except Exception as log_error:
            logger.error(f"Failed to log navigation error: {log_error}")
        
        # Fallback: Show error message and provide alternative navigation
        st.error(error_msg)
        fallback_navigation(movie_id, movie_title)

def fallback_navigation(movie_id: int, movie_title: str = ""):
    """
    Provides HTML fallback navigation when Streamlit navigation fails.
    
    Args:
        movie_id (int): The TMDB movie ID
        movie_title (str): Movie title for display
    """
    st.markdown(
        f"""
        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 8px; margin: 1rem 0;">
            <h4>Navigation Issue</h4>
            <p>Could not navigate automatically. Click the button below to view details for:</p>
            <p><strong>{movie_title or f'Movie ID: {movie_id}'}</strong></p>
            <a href="?movie_id={movie_id}" target="_self">
                <button style="background-color: #007bff; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer;">
                    View Details
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

def create_movie_poster_fallback(movie_id: int, poster_url: str, movie_title: str, width: int = 200):
    """
    Creates an HTML clickable poster fallback for when Streamlit navigation fails.
    
    Args:
        movie_id (int): The TMDB movie ID
        poster_url (str): URL of the movie poster
        movie_title (str): Movie title for alt text
        width (int): Width of the poster image
        
    Returns:
        str: HTML string for the clickable poster
    """
    return f"""
    <a href="?movie_id={movie_id}" target="_self" style="text-decoration: none;">
        <img src="{poster_url}" alt="{movie_title}" width="{width}" 
             style="border-radius: 8px; cursor: pointer; transition: transform 0.2s;"
             onmouseover="this.style.transform='scale(1.05)'"
             onmouseout="this.style.transform='scale(1)'">
    </a>
    """

def back_button_style():
    """
    Applies consistent CSS styling for back buttons across the app.
    Called once in your main app configuration.
    """
    st.markdown(
        """
        <style>
        /* Consistent back button styling */
        div.stButton > button:first-child {
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        div.stButton > button:first-child:hover {
            transform: translateX(-3px);
        }
        
        /* Style for fallback navigation button */
        .fallback-nav {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            border: 1px solid #dee2e6;
        }
        
        .fallback-nav button {
            background-color: #007bff;
            color: white;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .fallback-nav button:hover {
            background-color: #0056b3;
        }
        </style>
        """,
        unsafe_allow_html=True
    )