# apps/common/templatetags/url_exists.py
from django import template
from django.urls import resolve, Resolver404

register = template.Library()

@register.simple_tag(takes_context=True)
def url_exists(context, view_name):
    try:
        resolve(view_name)
        return True
    except Resolver404:
        return False