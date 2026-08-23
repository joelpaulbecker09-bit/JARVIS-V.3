import datetime
import os
import platform
import subprocess


def get_current_time() -> str:
    """Returns current system time and date formatted for German."""
    now = datetime.datetime.now()
    days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    day_name = days[now.weekday()]
    return f"Es ist {day_name}, der {now.strftime('%d.%m.%Y')}, {now.strftime('%H:%M:%S')} Uhr."


def get_system_info() -> str:
    """Returns system specs and status."""
    info = [
        f"Betriebssystem: {platform.system()} {platform.release()} ({platform.architecture()[0]})",
        f"Prozessor: {platform.processor() or 'x86_64'}",
        f"Computer Name: {platform.node()}"
    ]
    return " | ".join(info)


def calculate(expression: str) -> str:
    """Evaluates basic mathematical expression safely."""
    try:
        # Safe math evaluation allowing basic numbers and operators
        allowed = set("0123456789+-*/()., ")
        clean_expr = expression.replace(",", ".")
        if not set(clean_expr).issubset(allowed):
            return "Fehler: Ungültiger mathematischer Ausdruck."

        result = eval(clean_expr, {"__builtins__": None}, {})
        return f"Ergebnis: {result}"
    except Exception as e:
        return f"Fehler bei der Berechnung: {e}"


def open_website(url: str) -> str:
    """Opens a website in default browser."""
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        os.system(f'start "" "{url}"')
        return f"Webseite {url} wurde im Browser geöffnet, Sir."
    except Exception as e:
        return f"Fehler beim Öffnen der Webseite: {e}"
