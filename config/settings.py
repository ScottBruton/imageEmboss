"""
Application settings management
"""
import json
import os
from typing import Dict, Any, Optional
from PySide6.QtCore import QSettings


class AppSettings:
    """Manages application settings"""
    
    def __init__(self):
        self.settings = QSettings("ImageEmboss", "Settings")
        self.defaults = {
            'window_geometry': None,
            'window_state': None,
            'last_image_path': '',
            'last_output_dir': '',
            'gpu_acceleration': True,
            'auto_save_results': True,
            'show_debug_info': False,
            'processing_quality': 'high',
            'default_mm_per_px': 0.25,
            'default_extrude_height': 1.0,
            'recent_files': [],
            'max_recent_files': 10
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value"""
        if default is None:
            default = self.defaults.get(key)
        return self.settings.value(key, default)
    
    def set(self, key: str, value: Any):
        """Set setting value"""
        self.settings.setValue(key, value)
    
    def get_window_geometry(self) -> Optional[bytes]:
        """Get saved window geometry"""
        return self.get('window_geometry')
    
    def set_window_geometry(self, geometry: bytes):
        """Save window geometry"""
        self.set('window_geometry', geometry)
    
    def get_window_state(self) -> Optional[bytes]:
        """Get saved window state"""
        return self.get('window_state')
    
    def set_window_state(self, state: bytes):
        """Save window state"""
        self.set('window_state', state)
    
    def get_last_image_path(self) -> str:
        """Get last opened image path"""
        return self.get('last_image_path', '')
    
    def set_last_image_path(self, path: str):
        """Set last opened image path"""
        self.set('last_image_path', path)
    
    def get_last_output_dir(self) -> str:
        """Get last output directory"""
        return self.get('last_output_dir', '')
    
    def set_last_output_dir(self, path: str):
        """Set last output directory"""
        self.set('last_output_dir', path)
    
    def is_gpu_acceleration_enabled(self) -> bool:
        """Check if GPU acceleration is enabled"""
        return self.get('gpu_acceleration', True)
    
    def set_gpu_acceleration(self, enabled: bool):
        """Enable/disable GPU acceleration"""
        self.set('gpu_acceleration', enabled)
    
    def is_auto_save_enabled(self) -> bool:
        """Check if auto-save is enabled"""
        return self.get('auto_save_results', True)
    
    def set_auto_save(self, enabled: bool):
        """Enable/disable auto-save"""
        self.set('auto_save_results', enabled)
    
    def is_debug_info_enabled(self) -> bool:
        """Check if debug info is enabled"""
        return self.get('show_debug_info', False)
    
    def set_debug_info(self, enabled: bool):
        """Enable/disable debug info"""
        self.set('show_debug_info', enabled)
    
    def get_processing_quality(self) -> str:
        """Get processing quality setting"""
        return self.get('processing_quality', 'high')
    
    def set_processing_quality(self, quality: str):
        """Set processing quality"""
        self.set('processing_quality', quality)
    
    def get_default_mm_per_px(self) -> float:
        """Get default mm per pixel"""
        return self.get('default_mm_per_px', 0.25)
    
    def set_default_mm_per_px(self, value: float):
        """Set default mm per pixel"""
        self.set('default_mm_per_px', value)
    
    def get_default_extrude_height(self) -> float:
        """Get default extrude height"""
        return self.get('default_extrude_height', 1.0)
    
    def set_default_extrude_height(self, value: float):
        """Set default extrude height"""
        self.set('default_extrude_height', value)
    
    def get_recent_files(self) -> list:
        """Get recent files list"""
        return self.get('recent_files', [])
    
    def add_recent_file(self, file_path: str):
        """Add file to recent files list"""
        recent_files = self.get_recent_files()
        
        # Remove if already exists
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # Add to beginning
        recent_files.insert(0, file_path)
        
        # Limit size
        max_files = self.get('max_recent_files', 10)
        recent_files = recent_files[:max_files]
        
        self.set('recent_files', recent_files)
    
    def clear_recent_files(self):
        """Clear recent files list"""
        self.set('recent_files', [])
    
    def export_settings(self, file_path: str):
        """Export settings to file"""
        try:
            settings_dict = {}
            for key in self.defaults.keys():
                settings_dict[key] = self.get(key)
            
            with open(file_path, 'w') as f:
                json.dump(settings_dict, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to export settings: {e}")
            return False
    
    def import_settings(self, file_path: str):
        """Import settings from file"""
        try:
            with open(file_path, 'r') as f:
                settings_dict = json.load(f)
            
            for key, value in settings_dict.items():
                if key in self.defaults:
                    self.set(key, value)
            
            return True
        except Exception as e:
            print(f"Failed to import settings: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        for key in self.defaults.keys():
            self.settings.remove(key)


# Global settings instance
app_settings = AppSettings()
