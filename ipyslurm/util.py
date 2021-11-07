import re


def sort_key_natural(s, _nsre=re.compile('([0-9]+)')):
    """Adapted from http://blog.codinghorror.com/sorting-for-humans-natural-sort-order."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, str(s))]
