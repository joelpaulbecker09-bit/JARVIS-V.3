import re
from typing import Dict, Any, Optional

from src.tools.web_search import web_search
from src.tools.weather import get_weather
from src.tools.system_tools import get_current_time, get_system_info, calculate, open_website


class ToolManager:
    """
    JARVIS Tool Manager. Detects intent and executes relevant tools.
    """

    def process_tools(self, message: str) -> Optional[str]:
        """
        Analyzes the user message and executes matching tools if applicable.
        Returns a context string with tool output to feed into LLM response generation, or None.
        """
        msg_lower = message.lower().strip()

        # 1. Time / Date query
        if any(keyword in msg_lower for keyword in ["wie spät", "uhrzeit", "welches datum", "welcher tag", "wieviel uhr"]):
            return f"[TOOL AUSGABE - UHRZEIT/DATUM]: {get_current_time()}"

        # 2. Weather query
        if "wetter" in msg_lower:
            # Extract location if mentioned
            match = re.search(r"wetter\s+(?:in|für|von|bei)?\s*([a-zA-ZäöüÄÖÜß\s\-]+)", msg_lower)
            location = match.group(1).strip() if match else "Berlin"
            # Remove common question words
            location = re.sub(r"\b(heute|morgen|aktuell|jetzt|wie|ist|wird)\b", "", location).strip()
            if not location:
                location = "Berlin"
            return f"[TOOL AUSGABE - WETTER]: {get_weather(location)}"

        # 3. System Info query
        if any(keyword in msg_lower for keyword in ["systemstatus", "system info", "pc info", "betriebssystem"]):
            return f"[TOOL AUSGABE - SYSTEM]: {get_system_info()}"

        # 4. Open Website query
        if any(keyword in msg_lower for keyword in ["öffne ", "gehe zu ", "starte webseite "]):
            match = re.search(r"(?:öffne|gehe zu|starte webseite)\s+([a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})", msg_lower)
            if match:
                url = match.group(1).strip()
                return f"[TOOL AUSGABE - WEBSEITE GEÖFFNET]: {open_website(url)}"

        # 5. Calculation query
        if any(keyword in msg_lower for keyword in ["berechne", "was ist ", "rechne "]) and any(c in msg_lower for c in ["+", "-", "*", "/", "^"]):
            expr_match = re.search(r"([0-9\.\,\s\+\-\*\/\(\)]+)", message)
            if expr_match:
                calc_res = calculate(expr_match.group(1))
                return f"[TOOL AUSGABE - RECHNER]: {calc_res}"

        # 6. Explicit Web Search query
        if any(keyword in msg_lower for keyword in ["suche nach", "google nach", "recherche", "wer ist", "was ist", "aktuelle news", "neueste"]):
            # Filter query out
            query = re.sub(r"^(suche nach|google nach|recherche|suche|wer ist|was ist)\s*", "", msg_lower).strip()
            if not query:
                query = message
            search_res = web_search(query)
            return f"[TOOL AUSGABE - WEB-SUCHE ({query})]:\n{search_res}"

        return None
