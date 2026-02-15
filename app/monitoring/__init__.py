"""Monitoring module for Prometheus metrics and middleware"""

# Don't eagerly import router to avoid circular dependencies
# Router is imported in main.py when needed

__all__ = ["router"]
