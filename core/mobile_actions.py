# -*- coding: utf-8 -*-
"""
core/mobile_actions.py
======================
Mobile Deep Link & Intent Generator for Recallyn.
"""
import urllib.parse

def build_email_intent(to: str, subject: str, body: str) -> str:
    safe_to = urllib.parse.quote(to)
    safe_subj = urllib.parse.quote(subject)
    safe_body = urllib.parse.quote(body)
    return f"mailto:{safe_to}?subject={safe_subj}&body={safe_body}"

def build_maps_intent(location: str) -> str:
    safe_loc = urllib.parse.quote(location)
    return f"https://www.google.com/maps/search/?api=1&query={safe_loc}"

def build_calendar_intent(title: str, details: str, location: str) -> str:
    safe_title = urllib.parse.quote(title)
    safe_details = urllib.parse.quote(details)
    safe_loc = urllib.parse.quote(location)
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={safe_title}&details={safe_details}&location={safe_loc}"

def build_share_intent(text: str) -> str:
    safe_text = urllib.parse.quote(text)
    return f"mailto:?subject=Shared%20Note&body={safe_text}"
