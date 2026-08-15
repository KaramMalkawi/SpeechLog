"""Helpers for deriving public display names from identity / legal names."""

from __future__ import annotations


def display_name_from_official_full_name(official_full_name: str) -> str:
    """First + last token from an official / OCR full name.

    Examples:
      "Rami Saleem Emile Janini" → "Rami Janini"
      "Jane Doe" → "Jane Doe"
      "Madonna" → "Madonna"
    """
    parts = [part for part in str(official_full_name or "").split() if part]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][:160]
    return f"{parts[0]} {parts[-1]}"[:160]
