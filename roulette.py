#!/usr/bin/env python

import argparse
import random
import re
import requests
from bs4 import BeautifulSoup

def fetch_page(url, headers=None):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FilmRouletteBot/1.0)"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content

def fetch_live_country_links():
    url = "https://en.wikipedia.org/wiki/Category:Films_by_country_and_genre"
    content = fetch_page(url)
    soup = BeautifulSoup(content, "html.parser")
    results = []
    # Look for all <a> tags that match the pattern "X films by genre"
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

def clean_url(url):
    prefix = "https://en.wikipedia.org"
    if url.startswith(prefix + prefix):
        return prefix + url[len(prefix)*2:]
    return url

def get_genre_links_from_live_page(url):
    content = fetch_page(url)
    soup = BeautifulSoup(content, "html.parser")
    results = []
    # First, try the container with id "mw-subcategories"
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
        # Fallback: look for a container with class "mw-category"
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

def get_film_titles_from_live_page(url):
    content = fetch_page(url)
    soup = BeautifulSoup(content, "html.parser")
    film_titles = []
    pages_div = soup.find("div", id="mw-pages")
    if pages_div:
        for li in pages_div.find_all("li"):
            film_titles.append(li.get_text(strip=True))
    return list(dict.fromkeys(film_titles))

def get_final_film_titles(url):
    # First, get films from the current genre page.
    films = get_film_titles_from_live_page(url)
    # Check for subgenre links.
    content = fetch_page(url)
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
    # If subgenre links exist, randomly decide to dive into one.
    if subgenre_links:
        if random.choice([True, False]):
            chosen = random.choice(subgenre_links)
            print("Diving into subgenre page:", chosen["url"])
            films = get_film_titles_from_live_page(chosen["url"])
            return films, chosen["subgenre"]
        else:
            return films, ""
    else:
        return films, ""

def main():
    parser = argparse.ArgumentParser(description="Film Roulette - Randomly pick films from Wikipedia")
    parser.add_argument("-n", type=int, default=1, help="Number of random films to list")
    args = parser.parse_args()
    
    results = []
    
    for i in range(args.n):
        # Step 1: Fetch live country links and randomly select one.
        country_links = fetch_live_country_links()
        if not country_links:
            print("No country links found.")
            return
        chosen_country = random.choice(country_links)
        chosen_country["genre_page_url"] = clean_url(chosen_country["genre_page_url"])
        
        # Step 2: Fetch genre links from the chosen country's genre page.
        genre_links = get_genre_links_from_live_page(chosen_country["genre_page_url"])
        if not genre_links:
            print(f"No genre links found for country {chosen_country['country']}. Skipping.")
            continue
        chosen_genre = random.choice(genre_links)
        
        # Step 3: Get film titles (and possibly subgenre) from the chosen genre page.
        films, subgenre = get_final_film_titles(chosen_genre["url"])
        if not films:
            print(f"No films found for genre {chosen_genre['genre']} in country {chosen_country['country']}. Skipping.")
            continue
        chosen_film = random.choice(films)
        
        results.append({
            "Country": chosen_country["country"],
            "Genre": chosen_genre["genre"],
            "Subgenre": subgenre,
            "Film": chosen_film
        })
    
    # Sort the results by Country, then Genre, then Subgenre, then Film.
    results.sort(key=lambda x: (x["Country"], x["Genre"], x["Subgenre"], x["Film"]))
    
    # Output the results as a formatted table.
    col_widths = {
        "Country": 20,
        "Genre": 30,
        "Subgenre": 30,
        "Film": 50
    }
    header = f"{'Country':<{col_widths['Country']}} {'Genre':<{col_widths['Genre']}} {'Subgenre':<{col_widths['Subgenre']}} {'Film':<{col_widths['Film']}}"
    print(header)
    print("-" * len(header))
    for row in results:
        print(f"{row['Country']:<{col_widths['Country']}} {row['Genre']:<{col_widths['Genre']}} {row['Subgenre']:<{col_widths['Subgenre']}} {row['Film']:<{col_widths['Film']}}")

if __name__ == "__main__":
    main()
