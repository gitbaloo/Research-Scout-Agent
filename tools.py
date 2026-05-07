import requests
import json
import logging

logger = logging.getLogger("tools")

def search_papers(query: str, min_citations: int = 0, year_after: int = 0, year_before: int = 9999, year_exact: int = 0) -> str:
    url = "https://api.openalex.org/works"

    filters = []
    if year_exact:
        filters.append(f"publication_year:{year_exact}")
    else:
        if year_after:
            filters.append(f"publication_year:>{year_after}")
        if year_before < 9999:
            filters.append(f"publication_year:<{year_before}")
    if min_citations:
        filters.append(f"cited_by_count:>{min_citations}")

    params = {
        "search": query,
        "per-page": 25,
        "sort": "cited_by_count:desc",
        "select": "title,authorships,publication_year,cited_by_count,doi,abstract_inverted_index",
    }
    if filters:
        params["filter"] = ",".join(filters)

    logger.info("search_papers called | query=%r | year_exact=%s | year_after=%s | year_before=%s | min_citations=%s",
                query, year_exact or None, year_after or None, year_before if year_before < 9999 else None, min_citations or None)

    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    papers = data.get("results", [])

    query_words = [w.lower() for w in query.split() if len(w) > 3]
    required_matches = max(1, len(query_words) // 2) if len(query_words) > 1 else 1

    result = []
    for paper in papers:
        year = paper.get("publication_year") or 0
        citations = paper.get("cited_by_count") or 0

        authors = [a["author"]["display_name"] for a in paper.get("authorships", [])]
        inverted = paper.get("abstract_inverted_index") or {}
        abstract_words = sorted(inverted.items(), key=lambda x: x[1][0])
        abstract = " ".join(word for word, _ in abstract_words)

        title = paper.get("title", "") or ""
        combined = (title + " " + abstract).lower()
        matched = sum(1 for term in query_words if term in combined)
        if matched < required_matches:
            continue

        result.append({
            "title": paper.get("title", "Unknown"),
            "year": year,
            "citations": citations,
            "doi": paper.get("doi", None),
            "authors": authors,
            "abstract": abstract,
        })

    logger.info("search_papers returned %d result(s) after keyword filtering (raw from API: %d)", len(result), len(papers))

    if not result:
        return "No papers found matching the given constraints."

    return json.dumps(result)
