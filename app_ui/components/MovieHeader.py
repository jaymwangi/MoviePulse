import streamlit as st
from media_assets.styles import load_css

def MovieHeader(movie_data, show_tagline=True, show_rating=True, variant="default"):
    """
    A reusable component to display movie header information consistently across pages.
    
    Parameters:
    -----------
    movie_data : dict
        Dictionary containing movie information with keys:
        - title (str): Movie title
        - year (int): Release year
        - rating (float): Movie rating (0-10)
        - tagline (str): Movie tagline
        - genres (list): List of genres (optional)
    
    show_tagline : bool, optional
        Whether to display the tagline (default: True)
    
    show_rating : bool, optional
        Whether to display the rating (default: True)
    
    variant : str, optional
        Style variant: "default", "compact", or "detailed" (default: "default")
    """
    
    # Load CSS styles
    load_css("components.css")
    
    # Validate required fields
    if not movie_data or "title" not in movie_data:
        st.error("Invalid movie data provided to MovieHeader")
        return
    
    # Extract data with defaults
    title = movie_data.get("title", "Unknown Title")
    year = movie_data.get("year")
    rating = movie_data.get("rating")
    tagline = movie_data.get("tagline", "")
    genres = movie_data.get("genres", [])
    
    # Determine container class based on variant
    container_class = f"movie-header movie-header--{variant}"
    
    # Render the header
    with st.container():
        st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
        
        # Title and year
        year_text = f" ({year})" if year else ""
        st.markdown(f'<h1 class="movie-header__title">{title}{year_text}</h1>', unsafe_allow_html=True)
        
        # Rating (if available and requested)
        if show_rating and rating is not None:
            rating_display = format_rating(rating)
            rating_class = get_rating_class(rating)
            st.markdown(
                f'<div class="movie-header__rating {rating_class}">{rating_display}</div>', 
                unsafe_allow_html=True
            )
        
        # Tagline (if available and requested)
        if show_tagline and tagline:
            st.markdown(f'<p class="movie-header__tagline">"{tagline}"</p>', unsafe_allow_html=True)
        
        # Genres (for detailed variant)
        if variant == "detailed" and genres:
            genres_html = " • ".join(genres)
            st.markdown(f'<div class="movie-header__genres">{genres_html}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def format_rating(rating):
    """Format rating for display"""
    if isinstance(rating, (int, float)):
        return f"{rating:.1f}/10"
    return str(rating)

def get_rating_class(rating):
    """Get CSS class based on rating value"""
    if isinstance(rating, (int, float)):
        if rating >= 8.0:
            return "rating-excellent"
        elif rating >= 6.0:
            return "rating-good"
        elif rating >= 4.0:
            return "rating-average"
        else:
            return "rating-poor"
    return "rating-unknown"
