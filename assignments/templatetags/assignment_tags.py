from django import template

register = template.Library()

@register.filter
def letter_index(value):
    return chr(ord('A') + value - 1)
