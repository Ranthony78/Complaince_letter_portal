# apps/common/templatetags/math_filters.py
from django import template

register = template.Library()

@register.filter
def negate(value):
    """Return negative of value"""
    try:
        return -value
    except (TypeError, ValueError):
        return 0