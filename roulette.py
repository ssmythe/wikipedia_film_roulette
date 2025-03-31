import argparse
import os
import time
import hashlib
import random
import re
import sys
import requests
from bs4 import BeautifulSoup

# Configuration for caching.
CACHE_DIR = "cache"
CACHE_EXPIRATION = 7 * 24 * 3600  # 1 week in seconds

# Global flags.
VERBOSE = False
DEBUG = False

def verbose_print(msg):
    if VERBOSE:
        print(msg)

def debug_print(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

def get_cache_filename(url, category):
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()
    filename = os.path.join(CACHE_DIR, category, f"{h}.html")
    return filename

def get_cached_page(url, category, headers=None):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FilmRouletteBot/1.0)"}
    filename = get_cache_filename(url, category)
    os.makedirs(os.path.join(CACHE_DIR, category), exist_ok=True)
    if os.path.exists(filename):
        mtime = os.path.getmtime(filename)
        if time.time() - mtime < CACHE_EXPIRATION:
            verbose_print(f"[Cache] Using cached {category} page for {url}")
            with open(filename, "rb") as f:
                return f.read()
    verbose_print(f"[Fetch] Fetching {category} page from {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    content = response.content
    with open(filename, "wb") as f:
        f.write(content)
    return content

def clean_url(url):
    prefix = "https://en.wikipedia.org"
    if url.startswith(prefix + prefix):
        return prefix + url[len(prefix)*2:]
    return url

def fetch_live_country_links():
    url = "https://en.wikipedia.org/wiki/Category:Films_by_country_and_genre"
    content = get_cached_page(url, "country")
    soup = BeautifulSoup(content, "html.parser")
    results = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        match = re.match(r"(.+?) films by genre", text, re.IGNORECASE)
        if match:
            country = match.group(1).strip()
            href = a["href"]
            results.append({
                "country": country,
                "genre_page_url": f"https://en.wikipedia.org{href}"
            })
    debug_print(f"Fetched {len(results)} country links.")
    return results

def get_genre_links_from_live_page(url):
    content = get_cached_page(url, "genre")
    soup = BeautifulSoup(content, "html.parser")
    results = []
    subcat_div = soup.find("div", id="mw-subcategories")
    if subcat_div:
        debug_print("mw-subcategories found; content:")
        debug_print(subcat_div.get_text(separator=" | ", strip=True))
        for a in subcat_div.find_all("a", href=True):
            genre_text = a.get_text(strip=True)
            results.append({
                "genre": genre_text,
                "url": f"https://en.wikipedia.org{a['href']}"
            })
    else:
        debug_print("No mw-subcategories container found; scanning entire page for genre links.")
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if "films" in text.lower():
                results.append({
                    "genre": text,
                    "url": f"https://en.wikipedia.org{a['href']}"
                })
    debug_print(f"Found {len(results)} genre links from {url}")
    return results

def get_film_titles_from_live_page(url, category="film"):
    content = get_cached_page(url, category)
    soup = BeautifulSoup(content, "html.parser")
    film_titles = []
    pages_div = soup.find("div", id="mw-pages")
    if pages_div:
        for li in pages_div.find_all("li"):
            film_titles.append(li.get_text(strip=True))
    return list(dict.fromkeys(film_titles))  # remove duplicates

def simplify_label(label, country):
    label = label.strip()
    if label.lower().startswith(country.lower()):
        label = label[len(country):].strip()
    label = re.sub(r'\bfilms\b', '', label, flags=re.IGNORECASE).strip()
    return label

def get_final_film_titles(url, desired_subgenre=None):
    if desired_subgenre:
        subgenre_slug = desired_subgenre.strip().replace(" ", "_")
        match = re.search(r"/Category:([A-Za-z0-9_\-]+)_films", url)
        if match:
            full_slug = match.group(1)
            if "_" in full_slug:
                country_slug = "_".join(full_slug.split("_")[:-1])
                subgenre_title = f"{country_slug}_{subgenre_slug}_films"
                subgenre_url = f"https://en.wikipedia.org/wiki/Category:{subgenre_title}"
                verbose_print(f"Using specified subgenre: {subgenre_title.replace('_', ' ')}")
                films = get_film_titles_from_live_page(subgenre_url, category="subgenre")
                return films, simplify_label(subgenre_title.replace("_", " "), country_slug.replace("_", " "))
        print(f"Error: Could not determine subgenre URL for '{desired_subgenre}'.", file=sys.stderr)
        sys.exit(1)

    films = get_film_titles_from_live_page(url, category="film")
    content = get_cached_page(url, "film")
    soup = BeautifulSoup(content, "html.parser")
    subgenre_links = []
    subcat_div = soup.find("div", id="mw-subcategories")
    if subcat_div:
        for a in subcat_div.find_all("a", href=True):
            subgenre_links.append({
                "url": f"https://en.wikipedia.org{a['href']}",
                "subgenre": a.get_text(strip=True)
            })
    if subgenre_links:
        if random.choice([True, False]):
            chosen = random.choice(subgenre_links)
            verbose_print(f"Diving into subgenre page: {chosen['url']}")
            films = get_film_titles_from_live_page(chosen["url"], category="subgenre")
            return films, simplify_label(chosen["subgenre"], "")
        elif films:
            return films, ""
        else:
            chosen = random.choice(subgenre_links)
            films = get_film_titles_from_live_page(chosen["url"], category="subgenre")
            return films, simplify_label(chosen["subgenre"], "")
    return films, ""

def main():
    global VERBOSE, DEBUG
    parser = argparse.ArgumentParser(description="Film Roulette - Randomly pick films from Wikipedia")
    parser.add_argument("-n", type=int, default=1, help="Number of random films to list out")
    parser.add_argument("-v", action="store_true", help="Enable verbose output")
    parser.add_argument("-d", action="store_true", help="Enable debug output (requires -v)")
    parser.add_argument("-c", type=str, help="Specify a country (e.g. 'American')")
    parser.add_argument("-g", type=str, help="Specify a genre (e.g. 'science fiction')")
    parser.add_argument("-s", type=str, help="Specify a subgenre (e.g. 'time travel')")
    args = parser.parse_args()
    VERBOSE = args.v
    DEBUG = args.d and args.v

    if DEBUG:
        debug_print(f"CLI Options: n={args.n}, country={args.c}, genre={args.g}, subgenre={args.s}")

    results = []
    attempts = 0
    max_attempts = args.n * 5  # Give up after too many duplicate retries

    while len(results) < args.n and attempts < max_attempts:
        if args.c:
            chosen_country = {
                "country": args.c,
                "genre_page_url": f"https://en.wikipedia.org/wiki/Category:{args.c.replace(' ', '_')}_films_by_genre"
            }
            verbose_print(f"Using specified country: {args.c}")
        else:
            country_links = fetch_live_country_links()
            chosen_country = random.choice(country_links)
            verbose_print(f"Randomly selected country: {chosen_country['country']}")

        if args.g:
            genre_slug = args.g.replace(" ", "_")
            if args.g.lower().endswith("films"):
                genre_title = genre_slug
            else:
                genre_title = f"{genre_slug}_films"
            genre_url = f"https://en.wikipedia.org/wiki/Category:{genre_title}"
            chosen_genre = {
                "genre": genre_title.replace("_", " "),
                "url": genre_url
            }
            verbose_print(f"Using specified genre: {chosen_genre['genre']}")
        else:
            genre_links = get_genre_links_from_live_page(chosen_country["genre_page_url"])
            chosen_genre = random.choice(genre_links)
            verbose_print(f"Randomly selected genre: {chosen_genre['genre']}")

        films, subgenre = get_final_film_titles(chosen_genre["url"], desired_subgenre=args.s)
        if not films:
            verbose_print(f"No films found for {chosen_genre['genre']} in {chosen_country['country']}. Skipping.")
            attempts += 1
            continue

        remaining_choices = list(set(films) - set(r["Film"] for r in results))
        if not remaining_choices:
            verbose_print("No more unique films available in this category.")
            attempts += 1
            continue

        chosen_film = random.choice(remaining_choices)
        results.append({
            "Country": chosen_country["country"],
            "Genre": simplify_label(chosen_genre["genre"], chosen_country["country"]),
            "Subgenre": simplify_label(subgenre, chosen_country["country"]),
            "Film": chosen_film
        })
        attempts += 1

    # Sort the results
    results.sort(key=lambda x: (x["Country"], x["Genre"], x["Subgenre"], x["Film"]))

    # Dynamically calculate column widths
    col_widths = {
        key: max(len(key), max((len(row[key]) for row in results), default=0)) + 2
        for key in ["Country", "Genre", "Subgenre", "Film"]
    }

    header = f"{'Country':<{col_widths['Country']}}{'Genre':<{col_widths['Genre']}}{'Subgenre':<{col_widths['Subgenre']}}{'Film':<{col_widths['Film']}}"
    print(header)
    print("-" * len(header))
    for row in results:
        print(f"{row['Country']:<{col_widths['Country']}}{row['Genre']:<{col_widths['Genre']}}{row['Subgenre']:<{col_widths['Subgenre']}}{row['Film']:<{col_widths['Film']}}")

if __name__ == "__main__":
    main()