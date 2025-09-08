import streamlit as st
import time

def render_quick_summary(summary_data):
    """
    Render a visually appealing quick summary section with themes and content flags.
    
    Args:
        summary_data (dict): Dictionary containing:
            - summary (str): The TL;DR summary text
            - themes (list): List of theme strings
            - content_flags (list): List of content warning flags (more descriptive name)
    """
    if summary_data is None:
        # Show shimmer loading state
        _render_shimmer_loading()
        return
    
    if not summary_data:
        st.info("No summary data available.")
        return
    
    # Container with subtle border
    with st.container():
        st.markdown("""
        <style>
        .quick-summary {
            border-left: 4px solid var(--secondary-color);
            padding: 0.5rem 1rem;
            margin: 1rem 0;
            background-color: var(--background-color-secondary);
            border-radius: 0 8px 8px 0;
        }
        .summary-text {
            font-size: 1.1rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
            color: var(--text-color);
        }
        .theme-pill {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            margin: 0.25rem;
            border-radius: 16px;
            background-color: var(--background-color);
            color: var(--text-color);
            font-size: 0.85rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
            cursor: pointer;
        }
        .theme-pill:hover {
            transform: translateY(-2px);
            box-shadow: 0 3px 6px rgba(0,0,0,0.15);
        }
        .content-flag {
            display: inline-flex;
            align-items: center;
            padding: 0.35rem 0.75rem;
            margin: 0.25rem;
            border-radius: 6px;
            background-color: color-mix(in srgb, var(--secondary-color) 10%, transparent);
            color: var(--secondary-color);
            font-size: 0.85rem;
            border: 1px solid color-mix(in srgb, var(--secondary-color) 20%, transparent);
        }
        .section-label {
            font-size: 0.9rem;
            font-weight: 600;
            color: color-mix(in srgb, var(--text-color) 60%, transparent);
            margin: 0.5rem 0 0.25rem 0;
        }
        
        /* Shimmer loading animation */
        @keyframes shimmer {
            0% { background-position: -468px 0 }
            100% { background-position: 468px 0 }
        }
        .shimmer {
            color: transparent;
            animation-duration: 1.5s;
            animation-fill-mode: forwards;
            animation-iteration-count: infinite;
            animation-name: shimmer;
            animation-timing-function: linear;
            background: var(--background-color);
            background: linear-gradient(to right, var(--background-color) 8%, color-mix(in srgb, var(--background-color) 90%, var(--text-color)) 18%, var(--background-color) 33%);
            background-size: 800px 104px;
            position: relative;
        }
        .shimmer-block {
            height: 1rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
        }
        .shimmer-pill {
            display: inline-block;
            height: 1.75rem;
            width: 5rem;
            margin: 0.25rem;
            border-radius: 16px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Process summary text (truncate if needed)
        summary = summary_data.get('summary', 'No summary available')
        if len(summary) > 120:
            summary = summary[:117] + "..."
        
        # Summary section
        st.markdown(f"""
        <div class="quick-summary">
            <div class="summary-text">✨ {summary}</div>
        """, unsafe_allow_html=True)
        
        # Themes section
        themes = summary_data.get('themes', [])
        if themes:
            st.markdown('<div class="section-label">Themes</div>', unsafe_allow_html=True)
            themes_html = ''.join([f'<span class="theme-pill" onclick="handleThemeClick(\'{theme}\')">{theme}</span>' for theme in themes])
            st.markdown(themes_html, unsafe_allow_html=True)
        
        # Content flags section (using the more descriptive key name)
        content_flags = summary_data.get('content_flags', [])
        if content_flags:
            st.markdown('<div class="section-label" style="margin-top: 0.75rem;">Content Notes</div>', unsafe_allow_html=True)
            flags_html = ''.join([f'<span class="content-flag">{flag}</span>' for flag in content_flags])
            st.markdown(flags_html, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add JavaScript for theme pill clicks
        st.markdown("""
        <script>
        function handleThemeClick(theme) {
            // This would typically be handled by Streamlit components
            // For now, we'll just log to console
            console.log("Theme clicked: " + theme);
            
            // In a real implementation, you might want to:
            // 1. Set a session state value
            // 2. Trigger a callback
            // 3. Navigate to a filtered view
        }
        </script>
        """, unsafe_allow_html=True)

def _render_shimmer_loading():
    """Render a shimmer loading effect while content is being fetched"""
    with st.container():
        st.markdown("""
        <div class="quick-summary">
            <div class="shimmer shimmer-block" style="width: 100%; height: 1.5rem; margin-bottom: 1rem;"></div>
            <div class="section-label">Themes</div>
            <div>
                <span class="shimmer shimmer-pill"></span>
                <span class="shimmer shimmer-pill"></span>
                <span class="shimmer shimmer-pill"></span>
            </div>
            <div class="section-label" style="margin-top: 0.75rem;">Content Notes</div>
            <div>
                <span class="shimmer shimmer-pill" style="width: 7rem;"></span>
                <span class="shimmer shimmer-pill" style="width: 8rem;"></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Backward compatibility function
def render_quick_summary_with_flags(summary_data):
    """
    Legacy support for components that still use 'flags' instead of 'content_flags'
    """
    if summary_data and 'flags' in summary_data and 'content_flags' not in summary_data:
        summary_data = summary_data.copy()
        summary_data['content_flags'] = summary_data.pop('flags')
    
    return render_quick_summary(summary_data)

# Example usage and testing
if __name__ == "__main__":
    st.title("Updated QuickSummary Component Demo")
    
    st.markdown("""
    This updated version uses `content_flags` instead of `flags` for better semantic naming,
    while maintaining backward compatibility.
    """)
    
    # Toggle between loading state and content
    show_loading = st.checkbox("Show loading state", value=False)
    
    if show_loading:
        # Show loading state
        _render_shimmer_loading()
        st.write("This simulates the loading state while data is being fetched...")
    else:
        # Sample data with the new content_flags key
        sample_data = {
            "summary": "A young wizard's journey through his first year at Hogwarts School of Witchcraft and Wizardry, where he discovers his magical heritage, makes friends, and confronts the dark wizard who killed his parents. This is a very long summary that should definitely be truncated to meet the 120 character limit requirement for TL;DR sections.",
            "themes": ["Friendship", "Courage", "Good vs Evil", "Coming of Age", "Magic"],
            "content_flags": ["⚠️ Fantasy Violence", "🐍 Mild Frightening Scenes", "💔 Emotional Themes"]
        }
        
        # Render the component
        render_quick_summary(sample_data)
        
        # Show the character count
        summary = sample_data.get('summary', '')
        st.caption(f"Original length: {len(summary)} characters, Truncated to: {min(120, len(summary))} characters")
        
        # Demonstrate backward compatibility
        st.divider()
        st.subheader("Backward Compatibility Test")
        
        # Sample data with the old flags key (for testing backward compatibility)
        legacy_data = {
            "summary": "A classic sci-fi adventure through space",
            "themes": ["Adventure", "Space", "Exploration"],
            "flags": ["🚀 Sci-fi action", "👽 Alien encounters"]
        }
        
        st.write("Testing with legacy data structure (using 'flags' instead of 'content_flags'):")
        render_quick_summary_with_flags(legacy_data)
    
    # Show code
    with st.expander("Component Code"):
        code = '''
        import streamlit as st

        def render_quick_summary(summary_data):
            """
            Render a visually appealing quick summary section with themes and content flags.
            
            Args:
                summary_data (dict): Dictionary containing:
                    - summary (str): The TL;DR summary text
                    - themes (list): List of theme strings
                    - content_flags (list): List of content warning flags (more descriptive name)
            """
            if summary_data is None:
                # Show shimmer loading state
                _render_shimmer_loading()
                return
            
            if not summary_data:
                st.info("No summary data available.")
                return
            
            # Container with subtle border
            with st.container():
                st.markdown("""
                <style>
                .quick-summary {
                    border-left: 4px solid var(--secondary-color);
                    padding: 0.5rem 1rem;
                    margin: 1rem 0;
                    background-color: var(--background-color-secondary);
                    border-radius: 0 8px 8px 0;
                }
                .summary-text {
                    font-size: 1.1rem;
                    font-weight: 500;
                    margin-bottom: 0.75rem;
                    color: var(--text-color);
                }
                .theme-pill {
                    display: inline-block;
                    padding: 0.25rem 0.75rem;
                    margin: 0.25rem;
                    border-radius: 16px;
                    background-color: var(--background-color);
                    color: var(--text-color);
                    font-size: 0.85rem;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    transition: all 0.2s ease;
                    cursor: pointer;
                }
                .theme-pill:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 3px 6px rgba(0,0,0,0.15);
                }
                .content-flag {
                    display: inline-flex;
                    align-items: center;
                    padding: 0.35rem 0.75rem;
                    margin: 0.25rem;
                    border-radius: 6px;
                    background-color: color-mix(in srgb, var(--secondary-color) 10%, transparent);
                    color: var(--secondary-color);
                    font-size: 0.85rem;
                    border: 1px solid color-mix(in srgb, var(--secondary-color) 20%, transparent);
                }
                .section-label {
                    font-size: 0.9rem;
                    font-weight: 600;
                    color: color-mix(in srgb, var(--text-color) 60%, transparent);
                    margin: 0.5rem 0 0.25rem 0;
                }
                
                /* Shimmer loading animation */
                @keyframes shimmer {
                    0% { background-position: -468px 0 }
                    100% { background-position: 468px 0 }
                }
                .shimmer {
                    color: transparent;
                    animation-duration: 1.5s;
                    animation-fill-mode: forwards;
                    animation-iteration-count: infinite;
                    animation-name: shimmer;
                    animation-timing-function: linear;
                    background: var(--background-color);
                    background: linear-gradient(to right, var(--background-color) 8%, color-mix(in srgb, var(--background-color) 90%, var(--text-color)) 18%, var(--background-color) 33%);
                    background-size: 800px 104px;
                    position: relative;
                }
                .shimmer-block {
                    height: 1rem;
                    margin-bottom: 0.5rem;
                    border-radius: 4px;
                }
                .shimmer-pill {
                    display: inline-block;
                    height: 1.75rem;
                    width: 5rem;
                    margin: 0.25rem;
                    border-radius: 16px;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Process summary text (truncate if needed)
                summary = summary_data.get('summary', 'No summary available')
                if len(summary) > 120:
                    summary = summary[:117] + "..."
                
                # Summary section
                st.markdown(f"""
                <div class="quick-summary">
                    <div class="summary-text">✨ {summary}</div>
                """, unsafe_allow_html=True)
                
                # Themes section
                themes = summary_data.get('themes', [])
                if themes:
                    st.markdown('<div class="section-label">Themes</div>', unsafe_allow_html=True)
                    themes_html = ''.join([f'<span class="theme-pill" onclick="handleThemeClick(\'{theme}\')">{theme}</span>' for theme in themes])
                    st.markdown(themes_html, unsafe_allow_html=True)
                
                # Content flags section (using the more descriptive key name)
                content_flags = summary_data.get('content_flags', [])
                if content_flags:
                    st.markdown('<div class="section-label" style="margin-top: 0.75rem;">Content Notes</div>', unsafe_allow_html=True)
                    flags_html = ''.join([f'<span class="content-flag">{flag}</span>' for flag in content_flags])
                    st.markdown(flags_html, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Add JavaScript for theme pill clicks
                st.markdown("""
                <script>
                function handleThemeClick(theme) {
                    // This would typically be handled by Streamlit components
                    // For now, we'll just log to console
                    console.log("Theme clicked: " + theme);
                    
                    // In a real implementation, you might want to:
                    // 1. Set a session state value
                    // 2. Trigger a callback
                    // 3. Navigate to a filtered view
                }
                </script>
                """, unsafe_allow_html=True)

        def _render_shimmer_loading():
            """Render a shimmer loading effect while content is being fetched"""
            with st.container():
                st.markdown("""
                <div class="quick-summary">
                    <div class="shimmer shimmer-block" style="width: 100%; height: 1.5rem; margin-bottom: 1rem;"></div>
                    <div class="section-label">Themes</div>
                    <div>
                        <span class="shimmer shimmer-pill"></span>
                        <span class="shimmer shimmer-pill"></span>
                        <span class="shimmer shimmer-pill"></span>
                    </div>
                    <div class="section-label" style="margin-top: 0.75rem;">Content Notes</div>
                    <div>
                        <span class="shimmer shimmer-pill" style="width: 7rem;"></span>
                        <span class="shimmer shimmer-pill" style="width: 8rem;"></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Backward compatibility function
        def render_quick_summary_with_flags(summary_data):
            """
            Legacy support for components that still use 'flags' instead of 'content_flags'
            """
            if summary_data and 'flags' in summary_data and 'content_flags' not in summary_data:
                summary_data = summary_data.copy()
                summary_data['content_flags'] = summary_data.pop('flags')
            
            return render_quick_summary(summary_data)
        '''
        st.code(code, language='python')