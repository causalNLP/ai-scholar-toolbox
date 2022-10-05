from difflib import SequenceMatcher

def get_str_similarity(a: str, b: str) -> float:
    """Calculate the similarity of two strings and return a similarity ratio."""
    return SequenceMatcher(None, a, b).ratio()