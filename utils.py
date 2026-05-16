import os
import json

def time_to_seconds(time_str) -> float:
    """
    Handles formats: HH:MM:SS, MM:SS.ms, or plain seconds/floats.
    """
    try:
        if isinstance(time_str, (int, float)):
            return float(time_str)
        if not time_str:
            return 0.0
        parts = str(time_str).split(':')
        if len(parts) == 3: # HH:MM:SS
            h, m, s = map(float, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2: # MM:SS.ms
            m, s = map(float, parts)
            return m * 60 + s
        elif len(parts) == 1: # SS.ms
            return float(parts[0])
        return 0.0
    except Exception:
        return 0.0

def seconds_to_time(seconds: float) -> str:
    """Converts seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"
