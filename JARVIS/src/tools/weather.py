import urllib.parse
import urllib.request
import json
import re

WEATHER_CODES = {
    0: "Klarer Himmel",
    1: "Überwiegend klar",
    2: "Teilweise bewölkt",
    3: "Bedeckt",
    45: "Nebel",
    48: "Raufrostnebel",
    51: "Leichter Nieselregen",
    53: "Mäßiger Nieselregen",
    55: "Dichter Nieselregen",
    61: "Leichter Regen",
    63: "Mäßiger Regen",
    65: "Starker Regen",
    71: "Leichter Schneefall",
    73: "Mäßiger Schneefall",
    75: "Starker Schneefall",
    80: "Leichte Regenschauer",
    81: "Mäßige Regenschauer",
    82: "Heftige Regenschauer",
    95: "Gewitter",
}


def get_weather(location: str = "Berlin") -> str:
    """
    Fetches weather information for a given location using Open-Meteo API.
    Returns clean text formatted in German without problematic emojis.
    """
    if not location or not location.strip():
        location = "Berlin"

    clean_loc = location.strip()
    encoded = urllib.parse.quote(clean_loc)

    # 1. Open-Meteo Geocoding + Weather API (reliable & fast)
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=de"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "JARVIS/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode("utf-8"))
            results = geo_data.get("results")
            if results:
                lat = results[0]["latitude"]
                lon = results[0]["longitude"]
                name = results[0].get("name", clean_loc)

                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                with urllib.request.urlopen(weather_url, timeout=5) as wresp:
                    wdata = json.loads(wresp.read().decode("utf-8"))
                    curr = wdata.get("current_weather", {})
                    temp = curr.get("temperature", "unbekannt")
                    wind = curr.get("windspeed", "unbekannt")
                    code = curr.get("weathercode", 0)
                    condition = WEATHER_CODES.get(code, "Bewölkt")

                    return f"Aktuelles Wetter in {name}: {condition}, {temp} Grad Celsius, Windgeschwindigkeit: {wind} km/h."
    except Exception as e:
        print(f"[WEATHER OPEN-METEO NOTICE] {e}")

    # 2. Fallback to wttr.in (clean text)
    try:
        url = f"https://wttr.in/{encoded}?format=%C:+%t,+Wind:+%w&lang=de"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            text = resp.read().decode("utf-8", errors="ignore").strip()
            # Remove any raw emojis
            clean_wttr = re.sub(r'[^\x00-\x7F\xc0-\xffäöüÄÖÜß]', '', text)
            if clean_wttr and "ERROR" not in clean_wttr.upper():
                return f"Wetterinformation für {clean_loc}: {clean_wttr}"
    except Exception as e:
        print(f"[WEATHER WTTR NOTICE] {e}")

    return f"Konnte die Wetterdaten für '{location}' momentan nicht abrufen, Sir."
