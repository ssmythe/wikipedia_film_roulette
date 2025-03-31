#!/usr/bin/env python

import random
import re
import requests
from bs4 import BeautifulSoup

def fetch_live_country_links():
    url = "https://en.wikipedia.org/wiki/Category:Films_by_country_and_genre"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FilmRouletteBot/1.0)"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
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
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FilmRouletteBot/1.0)"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    results = []
    # Try to locate subcategories in a container with id "mw-subcategories"
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
        # Fallback: try the container with class "mw-category"
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
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FilmRouletteBot/1.0)"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    film_titles = []
    pages_div = soup.find("div", id="mw-pages")
    if pages_div:
        for li in pages_div.find_all("li"):
            film_titles.append(li.get_text(strip=True))
    return list(dict.fromkeys(film_titles))

def get_final_film_titles(url):
    # First, get films on the current page.
    films = get_film_titles_from_live_page(url)
    # Check if there are subgenre links.
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FilmRouletteBot/1.0)"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
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
                        subgenre_links.append(f"https://en.wikipedia.org{a['href']}")
    # If subgenre links exist, randomly decide to dive into one.
    if subgenre_links:
        if random.choice([True, False]):
            chosen_subgenre_url = random.choice(subgenre_links)
            print("Diving into subgenre page:", chosen_subgenre_url)
            return get_film_titles_from_live_page(chosen_subgenre_url)
        else:
            if films:
                return films
            else:
                chosen_subgenre_url = random.choice(subgenre_links)
                print("No films on current page; diving into subgenre page:", chosen_subgenre_url)
                return get_film_titles_from_live_page(chosen_subgenre_url)
    else:
        return films

def main():
    # Fetch live country links from the top-level page.
    country_links = fetch_live_country_links()
    if not country_links:
        print("No country links found.")
        return
    chosen_country = random.choice(country_links)
    chosen_country["genre_page_url"] = clean_url(chosen_country["genre_page_url"])
    print("Randomly selected country:", chosen_country["country"])
    print("Country genre page URL:", chosen_country["genre_page_url"])
    
    # Fetch genre links from the chosen country's genre page.
    genre_links = get_genre_links_from_live_page(chosen_country["genre_page_url"])
    if not genre_links:
        print("No genre links found on the country page.")
        return
    chosen_genre = random.choice(genre_links)
    print("Randomly selected genre:", chosen_genre["genre"])
    print("Genre page URL:", chosen_genre["url"])
    
    # Get film titles from the chosen genre (or subgenre) page.
    film_titles = get_final_film_titles(chosen_genre["url"])
    if not film_titles:
        print("No films found on the genre page.")
        return
    chosen_film = random.choice(film_titles)
    print("Randomly selected film:", chosen_film)

if __name__ == "__main__":
    main()
