def format_duration(seconds):
    """Format duration in hours, minutes and seconds.
    
    Args:
        seconds (float): Duration in seconds
        
    Returns:
        str: Formatted duration string (e.g. "2h 30m 15s" or "45m 30s" or "30s")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s" 