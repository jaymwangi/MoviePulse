from .theme_applier import apply_theme_settings, inject_custom_css
from .spoiler_handler import apply_spoiler_protection, spoiler_wrapper
from .settings_handler import handle_settings_change

__all__ = [
    'apply_theme_settings',
    'inject_custom_css',
    'apply_spoiler_protection',
    'spoiler_wrapper',
    'handle_settings_change'
]
