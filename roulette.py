#!/usr/bin/env python

import argparse
import os
import time
import hashlib
import random
import re
import requests
from bs4 import BeautifulSoup

# Configuration for caching.
CACHE_DIR = "cache"
CACHE_EXPIRATION = 7 * 24 * 3600  # 1 week in seconds

# Global variable for verbose output.
VERBOSE = False

def verbose_print(msg):
    if VERBOSE:
        print(msg)

def get_cache_filename(url, category):
    # Create a SHA-256 hash of the URL to use as a filename.
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
    return results

def get_genre_links_from_live_page(url):
    content = get_cached_page(url, "genre")
    soup = BeautifulSoup(content, "html.parser")
    results = []
    subcat_div = soup.find("div", id="mw-subcategories")
    if subcat_div:
        groups = subcat_div.find_all("div", class_="mw-category-group")
        for group in groups:
            ul = group.find("ul")
            if ul:
                for li in ul.find_all("li"):
                    a = li.find("a")
                    if a and a.get("href"):
                        genre_text = a.get_text(strip=True)
                        results.append({
                            "genre": genre_text,
                            "url": f"https://en.wikipedia.org{a['href']}"
                        })
    else:
        cat_div = soup.find("div", class_="mw-category")
        if cat_div:
            groups = cat_div.find_all("div", class_="mw-category-group")
            for group in groups:
                ul = group.find("ul")
                if ul:
                    for li in ul.find_all("li"):
                        a = li.find("a")
                        if a and a.get("href"):
                            genre_text = a.get_text(strip=True)
                            results.append({
                                "genre": genre_text,
                                "url": f"https://en.wikipedia.org{a['href']}"
                            })
    return results

def get_film_titles_from_live_page(url, category="film"):
    content = get_cached_page(url, category)
    soup = BeautifulSoup(content, "html.parser")
    film_titles = []
    pages_div = soup.find("div", id="mw-pages")
    if pages_div:
        for li in pages_div.find_all("li"):
            film_titles.append(li.get_text(strip=True))
    return list(dict.fromkeys(film_titles))

def get_final_film_titles(url):
    films = get_film_titles_from_live_page(url, category="film")
    content = get_cached_page(url, "film")
    soup = BeautifulSoup(content, "html.parser")
    subgenre_links = []
    subcat_div = soup.find("div", id="mw-subcategories")
    if subcat_div:
        groups = subcat_div.find_all("div", class_="mw-category-group")
        for group in groups:
            ul = group.find("ul")
            if ul:
                for li in ul.find_all("li"):
                    a = li.find("a")
                    if a and a.get("href"):
                        subgenre_links.append({
                            "url": f"https://en.wikipedia.org{a['href']}",
                            "subgenre": a.get_text(strip=True)
                        })
    if subgenre_links:
        if random.choice([True, False]):
            chosen = random.choice(subgenre_links)
            verbose_print(f"Diving into subgenre page: {chosen['url']}")
            films = get_film_titles_from_live_page(chosen["url"], category="subgenre")
            return films, chosen["subgenre"]
        else:
            if films:
                return films, ""
            else:
                chosen = random.choice(subgenre_links)
                verbose_print(f"No films on current page; diving into subgenre page: {chosen['url']}")
                films = get_film_titles_from_live_page(chosen["url"], category="subgenre")
                return films, chosen["subgenre"]
    else:
        return films, ""

def main():
    global VERBOSE
    parser = argparse.ArgumentParser(description="Film Roulette - Randomly pick films from Wikipedia")
    parser.add_argument("-n", type=int, default=1, help="Number of random films to list out")
    parser.add_argument("-v", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    VERBOSE = args.v

    results = []
    for i in range(args.n):
        # Step 1: Fetch live country links and randomly select one.
        country_links = fetch_live_country_links()
        if not country_links:
            verbose_print("No country links found.")
            return
        chosen_country = random.choice(country_links)
        chosen_country["genre_page_url"] = clean_url(chosen_country["genre_page_url"])
        verbose_print(f"Selected country: {chosen_country['country']}")
        verbose_print(f"Country genre page URL: {chosen_country['genre_page_url']}")

        # Step 2: Fetch genre links from the chosen country's page.
        genre_links = get_genre_links_from_live_page(chosen_country["genre_page_url"])
        if not genre_links:
            verbose_print(f"No genre links found for {chosen_country['country']}. Skipping.")
            continue
        chosen_genre = random.choice(genre_links)
        verbose_print(f"Selected genre: {chosen_genre['genre']}")
        verbose_print(f"Genre page URL: {chosen_genre['url']}")

        # Step 3: Get film titles (and possibly subgenre) from the chosen genre page.
        films, subgenre = get_final_film_titles(chosen_genre["url"])
        if not films:
            verbose_print(f"No films found for {chosen_genre['genre']} in {chosen_country['country']}. Skipping.")
            continue
        chosen_film = random.choice(films)
        results.append({
            "Country": chosen_country["country"],
            "Genre": chosen_genre["genre"],
            "Subgenre": subgenre,
            "Film": chosen_film
        })

    results.sort(key=lambda x: (x["Country"], x["Genre"], x["Subgenre"], x["Film"]))
    col_widths = {"Country": 20, "Genre": 30, "Subgenre": 30, "Film": 50}
    header = f"{'Country':<{col_widths['Country']}} {'Genre':<{col_widths['Genre']}} {'Subgenre':<{col_widths['Subgenre']}} {'Film':<{col_widths['Film']}}"
    print(header)
    print("-" * len(header))
    for row in results:
        print(f"{row['Country']:<{col_widths['Country']}} {row['Genre']:<{col_widths['Genre']}} {row['Subgenre']:<{col_widths['Subgenre']}} {row['Film']:<{col_widths['Film']}}")

if __name__ == "__main__":
    main()
