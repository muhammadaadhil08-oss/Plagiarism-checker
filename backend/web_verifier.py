"""
Web Verification Module
Searches the internet for matching content to verify if text is original or copied.
Uses DuckDuckGo (primary) and Bing (fallback) for reliable search results.
"""

import re
import math
import urllib.request
import urllib.parse
import urllib.error
import ssl
from difflib import SequenceMatcher

# Ignore SSL certificate errors to prevent failures
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}

# ─── SEARCH ENGINES ────────────────────────────────────────────────────

def _search_duckduckgo(query, timeout=4):
    """Search DuckDuckGo HTML (more permissive than Google)."""
    search_url = 'https://html.duckduckgo.com/html/?' + urllib.parse.urlencode({
        'q': query,
    })
    req = urllib.request.Request(search_url, headers=HEADERS)
    response = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    html = response.read().decode('utf-8', errors='ignore')

    snippets = []
    urls = []

    # DuckDuckGo HTML result blocks have class="result__snippet"
    snippet_matches = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div|span)',
        html, re.DOTALL | re.IGNORECASE
    )
    for s in snippet_matches:
        clean = re.sub(r'<[^>]+>', '', s).strip()
        clean = re.sub(r'\s+', ' ', clean)
        if len(clean) > 30:
            snippets.append(clean[:400])

    # Extract URLs from DuckDuckGo results
    url_matches = re.findall(
        r'class="result__url"[^>]*href="([^"]*)"',
        html, re.IGNORECASE
    )
    if not url_matches:
        url_matches = re.findall(
            r'class="result__a"[^>]*href="[^"]*uddg=([^&"]+)',
            html, re.IGNORECASE
        )
    for u in url_matches[:10]:
        decoded = urllib.parse.unquote(u).strip()
        if decoded.startswith('//'):
            decoded = 'https:' + decoded
        if decoded.startswith('http') and 'duckduckgo.com' not in decoded:
            urls.append(decoded)

    # Fallback: also try extracting URLs from href="/url?q=..." or href="https://..."
    if not urls:
        direct_urls = re.findall(
            r'href="(https?://[^"]+)"',
            html, re.IGNORECASE
        )
        for u in direct_urls:
            decoded = urllib.parse.unquote(u)
            if not any(x in decoded for x in ['duckduckgo.com', 'google.com', 'bing.com']):
                urls.append(decoded)
                if len(urls) >= 8:
                    break

    return snippets[:15], urls[:8]


def _search_bing(query, timeout=4):
    """Search Bing as fallback."""
    search_url = 'https://www.bing.com/search?' + urllib.parse.urlencode({
        'q': query,
        'count': '5',
    })
    req = urllib.request.Request(search_url, headers=HEADERS)
    response = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    html = response.read().decode('utf-8', errors='ignore')

    snippets = []
    urls = []

    # Bing caption snippets
    caption_matches = re.findall(
        r'<p[^>]*>(.*?)</p>',
        html, re.DOTALL | re.IGNORECASE
    )
    for s in caption_matches:
        clean = re.sub(r'<[^>]+>', '', s).strip()
        clean = re.sub(r'\s+', ' ', clean)
        if len(clean) > 40 and not clean.startswith('{'):
            snippets.append(clean[:400])

    # Bing URLs
    url_matches = re.findall(
        r'<a[^>]+href="(https?://[^"]+)"[^>]*>\s*<h2',
        html, re.IGNORECASE
    )
    if not url_matches:
        url_matches = re.findall(
            r'href="(https?://[^"]+)"',
            html, re.IGNORECASE
        )
    for u in url_matches:
        decoded = urllib.parse.unquote(u)
        if not any(x in decoded for x in ['bing.com', 'microsoft.com', 'msn.com']):
            urls.append(decoded)
            if len(urls) >= 8:
                break

    return snippets[:15], urls[:8]


# ─── SIMILARITY ────────────────────────────────────────────────────────

def _compute_snippet_similarity(input_text, snippet):
    """Compute similarity by finding exact phrase matches to detect direct copying."""
    input_norm = re.sub(r'\s+', ' ', input_text.lower().strip())
    snippet_norm = re.sub(r'\s+', ' ', snippet.lower().strip())

    input_words = input_norm.split()
    snippet_words = snippet_norm.split()

    if len(snippet_words) < 5:
        return 0.0

    # Strong exact phrase matches (15, 10, or 6 words in a row)
    for length, weight in [(15, 1.0), (10, 0.75), (6, 0.45)]:
        if len(snippet_words) >= length:
            for i in range(len(snippet_words) - length + 1):
                phrase = ' '.join(snippet_words[i:i+length])
                if phrase in input_norm:
                    return weight

    # Fallback to n-gram overlap within the snippet
    if len(input_words) >= 3 and len(snippet_words) >= 3:
        input_ngrams = set(' '.join(input_words[i:i+3]) for i in range(len(input_words)-2))
        snippet_ngrams = set(' '.join(snippet_words[i:i+3]) for i in range(len(snippet_words)-2))
        
        if snippet_ngrams:
            overlap = len(input_ngrams & snippet_ngrams)
            ratio = overlap / len(snippet_ngrams)
            return min(0.35, ratio) # Max 35% if just scattered random words matching

    return 0.0


# ─── MAIN SEARCH FUNCTION ─────────────────────────────────────────────

def search_web(text, num_queries=2, timeout=4):
    """
    Search the web for the given text to verify originality.
    Uses DuckDuckGo (primary) with Bing fallback.
    Reduced queries to 2 and timeout to 4s to prevent Gunicorn 30-sec worker timeout.

    Args:
        text: The text to verify
        num_queries: Number of search queries to run
        timeout: Timeout per request in seconds

    Returns:
        dict with:
            web_score (int): 0-100 how much of the text appears online
            sources (list): List of matched sources with url, snippet, similarity
            searched (bool): Whether the search was successfully performed
            error (str or None): Error message if search failed
    """
    if not text or len(text.strip()) < 30:
        return {
            "web_score": 0,
            "sources": [],
            "searched": False,
            "error": "Text too short for web verification"
        }

    # Build search queries from key sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return {
            "web_score": 0,
            "sources": [],
            "searched": False,
            "error": "No searchable sentences found"
        }

    # Pick distinctive sentences as queries
    queries = []
    queries.append(sentences[0][:120])
    if len(sentences) > 1:
        longest = max(sentences, key=len)
        if longest != sentences[0]:
            queries.append(longest[:120])
    if len(sentences) > 2:
        queries.append(sentences[len(sentences) // 2][:120])
    queries = queries[:num_queries]

    all_snippets = []
    all_urls = []
    search_worked = False
    search_engine_used = None

    # Try DuckDuckGo first, then Bing as fallback
    for query in queries:
        found = False

        # Try DuckDuckGo
        try:
            snippets, urls = _search_duckduckgo(f'"{query}"', timeout=timeout)
            if snippets or urls:
                all_snippets.extend(snippets)
                all_urls.extend(urls)
                search_worked = True
                found = True
                search_engine_used = search_engine_used or "DuckDuckGo"
        except Exception:
            pass

        # If DuckDuckGo failed, try Bing
        if not found:
            try:
                snippets, urls = _search_bing(f'"{query}"', timeout=timeout)
                if snippets or urls:
                    all_snippets.extend(snippets)
                    all_urls.extend(urls)
                    search_worked = True
                    search_engine_used = search_engine_used or "Bing"
            except Exception:
                pass

    if not search_worked:
        return {
            "web_score": 0,
            "sources": [],
            "searched": False,
            "error": "Could not reach search engines. Check your internet connection."
        }

    # Compare input text against all found snippets
    max_similarity = 0.0

    # Deduplicate URLs by domain
    seen_domains = set()
    unique_urls = []
    for url in all_urls:
        domain = re.sub(r'https?://(www\.)?', '', url).split('/')[0]
        if domain not in seen_domains:
            seen_domains.add(domain)
            unique_urls.append(url)

    # Check similarity
    for snippet in all_snippets:
        sim = _compute_snippet_similarity(text, snippet)
        if sim > 0.15:
            max_similarity = max(max_similarity, sim)

    # Build source list with best matching snippet per URL
    matched_sources = []
    for url in unique_urls[:6]:
        best_sim = 0
        best_snippet = ""
        for snippet in all_snippets:
            sim = _compute_snippet_similarity(text, snippet)
            if sim > best_sim:
                best_sim = sim
                best_snippet = snippet[:180]

        if best_sim > 0.08:
            matched_sources.append({
                "url": url,
                "snippet": best_snippet + "..." if len(best_snippet) >= 180 else best_snippet,
                "similarity": round(best_sim * 100)
            })

    # Sort by similarity descending
    matched_sources.sort(key=lambda x: x["similarity"], reverse=True)
    matched_sources = matched_sources[:5]

    # Calculate web score
    web_score = round(max_similarity * 100)
    web_score = max(0, min(100, web_score))

    return {
        "web_score": web_score,
        "sources": matched_sources,
        "searched": True,
        "error": None,
        "engine": search_engine_used,
    }
