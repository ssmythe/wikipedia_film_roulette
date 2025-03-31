#!/usr/bin/env python

import argparse
import os
import time
import hashlib
import random
import re
import sys
import requests
from bs4 import BeautifulSoup
import difflib

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

def clean_url(url):
    url = url.strip()
    if url.startswith("http"):
        return url
    if url.startswith("//"):
        return f"https:{url}"
    return f"https://en.wikipedia.org{url}"

def get_cached_page(url, category, headers=None):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FilmRouletteBot/1.0)"}
    url = clean_url(url)
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
    if url.startswith("http"):
        return url
    return f"https://en.wikipedia.org{url}"



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
            results.append(
                {
                    "country": country,
                    "genre_page_url": f"https://en.wikipedia.org{href}",
                }
            )
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
            results.append(
                {"genre": genre_text, "url": f"https://en.wikipedia.org{a['href']}"}
            )
    else:
        debug_print(
            "No mw-subcategories container found; scanning entire page for genre links."
        )
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if "films" in text.lower():
                results.append(
                    {"genre": text, "url": f"https://en.wikipedia.org{a['href']}"}
                )
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
        label = label[len(country) :].strip()
    label = re.sub(r"\bfilms\b", "", label, flags=re.IGNORECASE).strip()
    return label


def suggest_closest(match_to, options):
    lower_match = match_to.lower()
    for option in options:
        if lower_match in option.lower():
            return option
    matches = difflib.get_close_matches(match_to, options, n=1, cutoff=0.5)
    return matches[0] if matches else None


def search_global_subgenre_links(country, genre):
    base_url = "https://en.wikipedia.org/wiki/Category:"
    keywords = [f"{country} {genre}".strip(), country, genre]
    options = []
    common_subgenres = [
        "time travel",
        "dystopian",
        "space opera",
        "cyberpunk",
        "alien invasion",
    ]
    for k in keywords:
        for sub in common_subgenres:
            cat = f"{k} {sub} films".replace("  ", " ")
            url = clean_url("/wiki/Category:" + "_".join(cat.split()))
            options.append({"subgenre": cat, "url": url})
    return options


def get_final_film_titles(url, desired_subgenre=None, country="", genre=""):
    content = get_cached_page(url, "film")
    soup = BeautifulSoup(content, "html.parser")
    subgenre_links = []
    seen_subgenres = set()

    subcat_div = soup.find("div", id="mw-subcategories")
    if subcat_div:
        for a in subcat_div.find_all("a", href=True):
            label = a.get_text(strip=True)
            if label not in seen_subgenres:
                subgenre_links.append(
                    {"url": f"https://en.wikipedia.org{a['href']}", "subgenre": label}
                )
                seen_subgenres.add(label)

    for a in soup.find_all("a", href=True):
        label = a.get_text(strip=True)
        if "film" in label.lower() and label not in seen_subgenres:
            subgenre_links.append(
                {"url": f"https://en.wikipedia.org{a['href']}", "subgenre": label}
            )
            seen_subgenres.add(label)

    if desired_subgenre:
        subgenre_names = [s["subgenre"] for s in subgenre_links]
        suggestion = suggest_closest(desired_subgenre, subgenre_names)
        if suggestion:
            matched = next(
                (s for s in subgenre_links if s["subgenre"] == suggestion), None
            )
            if matched:
                verbose_print(
                    f"Using subgenre '{suggestion}' (matched from '{desired_subgenre}')"
                )
                films = get_film_titles_from_live_page(
                    matched["url"], category="subgenre"
                )
                return films, simplify_label(matched["subgenre"], "")

        guessed_links = search_global_subgenre_links(country, genre)
        guessed_names = [g["subgenre"] for g in guessed_links]
        guessed_suggestion = suggest_closest(desired_subgenre, guessed_names)
        if guessed_suggestion:
            guessed_match = next(
                g for g in guessed_links if g["subgenre"] == guessed_suggestion
            )
            verbose_print(
                f"Using guessed global subgenre '{guessed_suggestion}' ({guessed_match['url']})"
            )
            films = get_film_titles_from_live_page(
                guessed_match["url"], category="subgenre"
            )
            return films, simplify_label(guessed_match["subgenre"], "")

        print(
            f"Error: Specified subgenre '{desired_subgenre}' not found.",
            file=sys.stderr,
        )
        sys.exit(1)

    films = get_film_titles_from_live_page(url, category="film")

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
    parser = argparse.ArgumentParser(
        description="Film Roulette - Randomly pick films from Wikipedia"
    )
    parser.add_argument(
        "-n", type=int, default=1, help="Number of random films to list out"
    )
    parser.add_argument("-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "-d", action="store_true", help="Enable debug output (requires -v)"
    )
    parser.add_argument("-c", type=str, help="Specify a country (e.g. 'American')")
    parser.add_argument("-g", type=str, help="Specify a genre (e.g. 'science fiction')")
    parser.add_argument("-s", type=str, help="Specify a subgenre (e.g. 'time travel')")
    args = parser.parse_args()
    VERBOSE = args.v
    DEBUG = args.d and args.v

    if DEBUG:
        debug_print(
            f"CLI Options: n={args.n}, country={args.c}, genre={args.g}, subgenre={args.s}"
        )

    results = []
    attempts = 0
    max_attempts = args.n * 5

    country_links = fetch_live_country_links()

    while len(results) < args.n and attempts < max_attempts:
        if args.c:
            country_names = [c["country"] for c in country_links]
            matching = [
                c for c in country_links if args.c.lower() == c["country"].lower()
            ]
            if matching:
                chosen_country = matching[0]
                verbose_print(f"Using specified country: {args.c}")
            else:
                suggestion = suggest_closest(args.c, country_names)
                if suggestion:
                    print(
                        f"Error: Specified country '{args.c}' not found. Did you mean '{suggestion}'?",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"Error: Specified country '{args.c}' not found.",
                        file=sys.stderr,
                    )
                sys.exit(1)
        else:
            chosen_country = random.choice(country_links)

        genre_links = get_genre_links_from_live_page(chosen_country["genre_page_url"])

        if args.g:
            genre_names = [
                simplify_label(g["genre"], chosen_country["country"])
                for g in genre_links
            ]
            filtered_genres = [
                g
                for g in genre_links
                if args.g.lower()
                in simplify_label(g["genre"], chosen_country["country"]).lower()
            ]
            if filtered_genres:
                chosen_genre = random.choice(filtered_genres)
            else:
                suggestion = suggest_closest(args.g, genre_names)
                if suggestion:
                    print(
                        f"Error: Specified genre '{args.g}' not found. Did you mean '{suggestion}'?",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"Error: Specified genre '{args.g}' not found.", file=sys.stderr
                    )
                sys.exit(1)
        else:
            chosen_genre = random.choice(genre_links)

        films, subgenre = get_final_film_titles(
            chosen_genre["url"], desired_subgenre=args.s
        )
        if not films:
            verbose_print(
                f"No films found for {chosen_genre['genre']} in {chosen_country['country']}. Skipping."
            )
            attempts += 1
            continue

        remaining_choices = list(set(films) - set(r["Film"] for r in results))
        if not remaining_choices:
            verbose_print("No more unique films available in this category.")
            attempts += 1
            continue

        chosen_film = random.choice(remaining_choices)
        results.append(
            {
                "Country": chosen_country["country"],
                "Genre": simplify_label(
                    chosen_genre["genre"], chosen_country["country"]
                ),
                "Subgenre": simplify_label(subgenre, chosen_country["country"]),
                "Film": chosen_film,
            }
        )
        attempts += 1

    results.sort(key=lambda x: (x["Country"], x["Genre"], x["Subgenre"], x["Film"]))
    col_widths = {
        key: max(len(key), max((len(row[key]) for row in results), default=0)) + 2
        for key in ["Country", "Genre", "Subgenre", "Film"]
    }
    header = f"{'Country':<{col_widths['Country']}}{'Genre':<{col_widths['Genre']}}{'Subgenre':<{col_widths['Subgenre']}}{'Film':<{col_widths['Film']}}"
    print(header)
    print("-" * len(header))
    for row in results:
        print(
            f"{row['Country']:<{col_widths['Country']}}{row['Genre']:<{col_widths['Genre']}}{row['Subgenre']:<{col_widths['Subgenre']}}{row['Film']:<{col_widths['Film']}}"
        )


if __name__ == "__main__":
    main()
