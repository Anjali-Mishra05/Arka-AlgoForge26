"""Analytics router — compute real analytics from MongoDB."""

from utils.analytics import get_analytics_summary


def get_analytics():
    """Return computed analytics summary."""
    return get_analytics_summary()
