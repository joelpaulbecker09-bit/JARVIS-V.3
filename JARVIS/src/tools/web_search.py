import urllib.parse
import urllib.request
import json
import re


def web_search(query: str, max_results: int = 4) -> str:
    """
    Performs a web search using DuckDuckGo Instant Answer API & HTML search.
    Returns a formatted summary string of search results.
    """
    if not query or not query.strip():
        return "Keine Suchanfrage angegeben."

    clean_query = query.strip()
    encoded = urllib.parse.quote(clean_query)

    results = []

    # 1. Try DuckDuckGo Instant Answer API
    try:
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            abstract = data.get("AbstractText", "")
            if abstract:
                results.append(f"Zusammenfassung: {abstract}")
            
            related = data.get("RelatedTopics", [])
            for item in related[:max_results]:
                if isinstance(item, dict) and "Text" in item:
                    results.append(f"- {item['Text']}")
    except Exception as e:
        print(f"[WEB SEARCH API NOTICE] {e}")

    # 2. Try DuckDuckGo Lite HTML Search if API yields few results
    if len(results) < 2:
        try:
            html_url = f"https://html.duckduckgo.com/html/?q={encoded}"
            req = urllib.request.Request(html_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            })
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                snippets = re.findall(r'<a class="result__snippet[^">]*>(.*?)</a>', html, re.DOTALL)
                titles = re.findall(r'<a class="result__url[^">]*>(.*?)</a>', html, re.DOTALL)

                for i in range(min(max_results, len(snippets))):
                    snip = re.sub(r'<.*?>', '', snippets[i]).strip()
                    if snip:
                        results.append(f"- {snip}")
        except Exception as e:
            print(f"[WEB SEARCH HTML NOTICE] {e}")

    if not results:
        return f"Keine Suchergebnisse im Web für '{query}' gefunden."

    return "\n".join(results[:6])
