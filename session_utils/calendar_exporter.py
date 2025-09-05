"""
Calendar Export Utilities

Handles exporting mood calendar data to various formats including ICS (iCalendar)
and CSV for backup and external calendar integration.
"""

import csv
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

# Try to import icalendar, but make it optional
try:
    from icalendar import Calendar, Event, vCalAddress, vText
    ICAL_AVAILABLE = True
except ImportError:
    ICAL_AVAILABLE = False
    logging.warning("icalendar package not available. ICS export will be disabled.")

logger = logging.getLogger(__name__)


class CalendarExporter:
    """Handles export of mood calendar data to various formats."""
    
    def __init__(self, mood_data: Dict[str, str], user_profile: Optional[Dict] = None):
        """
        Initialize the calendar exporter.
        
        Args:
            mood_data: Dictionary with date strings as keys and mood values
            user_profile: Optional user profile information for metadata
        """
        self.mood_data = mood_data
        self.user_profile = user_profile or {}
        
    def export_ics(self, output_path: Union[str, Path]) -> bool:
        """
        Export mood calendar to ICS format for calendar applications.
        
        Args:
            output_path: Path where the .ics file should be saved
            
        Returns:
            bool: True if export was successful, False otherwise
        """
        if not ICAL_AVAILABLE:
            logger.error("ICS export requires icalendar package. Install with: pip install icalendar")
            return False
            
        try:
            cal = Calendar()
            cal.add('prodid', '-//Mood Calendar//movie-recs.com//')
            cal.add('version', '2.0')
            cal.add('name', 'Mood Calendar')
            cal.add('x-wr-calname', 'Mood Tracking Calendar')
            
            # Add events for each mood entry
            for date_str, mood in self.mood_data.items():
                event = self._create_mood_event(date_str, mood)
                if event:
                    cal.add_component(event)
            
            # Write to file
            with open(output_path, 'wb') as f:
                f.write(cal.to_ical())
            
            logger.info(f"Successfully exported {len(self.mood_data)} mood entries to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export ICS file: {str(e)}")
            return False
    
    def _create_mood_event(self, date_str: str, mood: str) -> Optional[Event]:
        """Create an ICS event for a mood entry."""
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            event = Event()
            event.add('summary', f'Mood: {mood.capitalize()}')
            event.add('dtstart', event_date)
            event.add('dtend', event_date + timedelta(days=1))  # All-day event
            event.add('dtstamp', datetime.now())
            event.add('uid', f'mood-{date_str}@movie-recs.com')
            
            # Add description with mood details
            description = f"Mood recorded: {mood.capitalize()}\n"
            description += f"Exported from Movie Recommendation System on {datetime.now().strftime('%Y-%m-%d')}"
            event.add('description', description)
            
            # Add categories for easier filtering
            event.add('categories', ['Mood Tracking', 'Personal'])
            
            return event
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid date format for mood event: {date_str} - {str(e)}")
            return None
    
    def export_csv(self, output_path: Union[str, Path]) -> bool:
        """
        Export mood calendar to CSV format for easy viewing and backup.
        
        Args:
            output_path: Path where the .csv file should be saved
            
        Returns:
            bool: True if export was successful, False otherwise
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'mood', 'day_of_week', 'week_number', 'export_date']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                for date_str, mood in sorted(self.mood_data.items()):
                    try:
                        event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        row = {
                            'date': date_str,
                            'mood': mood,
                            'day_of_week': event_date.strftime('%A'),
                            'week_number': event_date.isocalendar()[1],
                            'export_date': datetime.now().strftime('%Y-%m-%d')
                        }
                        writer.writerow(row)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping invalid date entry: {date_str} - {str(e)}")
                        continue
            
            logger.info(f"Successfully exported {len(self.mood_data)} mood entries to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export CSV file: {str(e)}")
            return False
    
    def export_json(self, output_path: Union[str, Path]) -> bool:
        """
        Export mood calendar to JSON format for data portability.
        
        Args:
            output_path: Path where the .json file should be saved
            
        Returns:
            bool: True if export was successful, False otherwise
        """
        try:
            export_data = {
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'version': '1.0',
                    'source': 'Movie Recommendation System',
                    'total_entries': len(self.mood_data)
                },
                'user_info': {
                    'username': self.user_profile.get('username', 'unknown'),
                    'exported_at': datetime.now().isoformat()
                },
                'mood_data': self.mood_data
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully exported {len(self.mood_data)} mood entries to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export JSON file: {str(e)}")
            return False
    
    def get_export_stats(self) -> Dict[str, any]:
        """
        Get statistics about the mood data being exported.
        
        Returns:
            Dictionary with export statistics
        """
        if not self.mood_data:
            return {'total_entries': 0, 'date_range': 'No data'}
        
        dates = sorted(self.mood_data.keys())
        try:
            start_date = min(datetime.strptime(d, '%Y-%m-%d') for d in dates)
            end_date = max(datetime.strptime(d, '%Y-%m-%d') for d in dates)
            date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        except (ValueError, TypeError):
            date_range = "Invalid date format"
        
        # Count mood frequencies
        mood_counts = {}
        for mood in self.mood_data.values():
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        return {
            'total_entries': len(self.mood_data),
            'date_range': date_range,
            'mood_distribution': mood_counts,
            'unique_moods': len(mood_counts),
            'most_common_mood': max(mood_counts.items(), key=lambda x: x[1])[0] if mood_counts else 'None'
        }


def export_calendar_data(mood_data: Dict[str, str], 
                        format_type: str = 'csv',
                        output_path: Optional[Union[str, Path]] = None,
                        user_profile: Optional[Dict] = None) -> bool:
    """
    Convenience function to export calendar data in various formats.
    
    Args:
        mood_data: Dictionary with date strings as keys and mood values
        format_type: One of 'csv', 'ics', or 'json'
        output_path: Optional output path (defaults to auto-generated name)
        user_profile: Optional user profile information
        
    Returns:
        bool: True if export was successful, False otherwise
    """
    if not mood_data:
        logger.warning("No mood data to export")
        return False
    
    exporter = CalendarExporter(mood_data, user_profile)
    
    # Generate default output path if not provided
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"mood_calendar_export_{timestamp}.{format_type}"
        output_path = Path.home() / "Downloads" / default_filename
    
    # Ensure output directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Perform export based on format
    if format_type.lower() == 'csv':
        return exporter.export_csv(output_path)
    elif format_type.lower() == 'ics':
        return exporter.export_ics(output_path)
    elif format_type.lower() == 'json':
        return exporter.export_json(output_path)
    else:
        logger.error(f"Unsupported export format: {format_type}")
        return False


def generate_sample_ics() -> str:
    """
    Generate a sample ICS file for testing purposes.
    
    Returns:
        str: ICS content as string
    """
    if not ICAL_AVAILABLE:
        return ""
    
    cal = Calendar()
    cal.add('prodid', '-//Mood Calendar Sample//movie-recs.com//')
    cal.add('version', '2.0')
    cal.add('name', 'Sample Mood Calendar')
    
    # Add sample events
    sample_dates = {
        '2024-01-15': 'uplifting',
        '2024-01-16': 'melancholic',
        '2024-01-17': 'energetic'
    }
    
    for date_str, mood in sample_dates.items():
        event = Event()
        event.add('summary', f'Mood: {mood.capitalize()}')
        event.add('dtstart', datetime.strptime(date_str, '%Y-%m-%d').date())
        event.add('dtend', datetime.strptime(date_str, '%Y-%m-%d').date() + timedelta(days=1))
        event.add('dtstamp', datetime.now())
        event.add('uid', f'sample-{date_str}@movie-recs.com')
        cal.add_component(event)
    
    return cal.to_ical().decode('utf-8')


# Example usage
if __name__ == "__main__":
    # Sample data for testing
    sample_mood_data = {
        '2024-01-15': 'uplifting',
        '2024-01-16': 'melancholic',
        '2024-01-17': 'energetic',
        '2024-01-18': 'relaxing',
        '2024-01-19': 'uplifting'
    }
    
    sample_profile = {'username': 'test_user'}
    
    # Test exports
    exporter = CalendarExporter(sample_mood_data, sample_profile)
    
    # Export to different formats
    exporter.export_csv('test_mood_export.csv')
    
    if ICAL_AVAILABLE:
        exporter.export_ics('test_mood_export.ics')
    
    exporter.export_json('test_mood_export.json')
    
    # Get statistics
    stats = exporter.get_export_stats()
    print(f"Export stats: {stats}")
