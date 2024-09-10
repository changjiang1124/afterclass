from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def letter_index(value):
    return chr(ord('A') + value - 1)

@register.filter
def days_until(value):
    delta = value - timezone.now()
    return max(delta.days + 1, 0)

@register.filter
def format_date(value):
    return value.strftime('%d/%m/%Y')
