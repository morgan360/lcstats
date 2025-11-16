"""
Custom template filters for animated solutions
"""

import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key.
    Usage: {{ dict|get_item:key }}
    """
    if dictionary and key in dictionary:
        return mark_safe(json.dumps(dictionary[key]))
    return None


@register.filter(name='to_json')
def to_json(value):
    """
    Convert a Python object to JSON.
    Usage: {{ value|to_json }}
    """
    return mark_safe(json.dumps(value))
