import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUTPUT_DIR = Path("movie_info")
MAX_WORKERS = 3

def extract_movie_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    scrtext_td = soup.find("td", class_="scrtext")
    if not scrtext_td:
        return None

    children = scrtext_td.find_all(recursive=False)
    meta_table = children[2] if len(children) > 2 and children[2].name == "table" else None
    script_pre = children[0] if len(children) > 0 and children[0].name == "pre" else None

    poster_url, poster_bytes = None, None
    writers, genres = [], []

    if meta_table:
        tds = meta_table.find_all("td")
        if tds:
            img_tag = tds[0].find("img")
            if img_tag and img_tag.has_attr("src"):
                poster_url = urljoin(url, img_tag["src"])
                try:
                    img_response = requests.get(poster_url, timeout=10)
                    img_response.raise_for_status()
                    poster_bytes = img_response.content
                except Exception as e:
                    print(f"Failed to download poster for {url}: {e}")
        if len(tds) > 1:
            info_td = tds[1]
            writers = [a.get_text(strip=True) for a in info_td.select("b:contains('Writers') ~ a")]
            genres = [a.get_text(strip=True) for a in info_td.select("b:contains('Genres') ~ a")]

    script_text = script_pre.get_text(strip=False) if script_pre else None

    return {
        "poster_url": poster_url,
        "poster_bytes": poster_bytes,
        "writers": writers,
        "genres": genres,
        "script": script_text,
        "movie_name": Path(urlparse(url).path).stem.replace("-", "_")
    }

def process_url(url):
    data = extract_movie_data(url)
    if not data:
        return

    movie_folder = OUTPUT_DIR / data["movie_name"]
    json_path = movie_folder / "info.json"
    image_path = movie_folder / "poster.jpg"

    if json_path.exists() and image_path.exists():
        print(f"[SKIP] {data['movie_name']} already processed.")
        return

    movie_folder.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_data = {
        "writers": data["writers"],
        "genres": data["genres"],
        "script": data["script"]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    # Save image
    if data["poster_bytes"]:
        with open(image_path, "wb") as img_file:
            img_file.write(data["poster_bytes"])

    print(f"[DONE] {data['movie_name']}")

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open("script_urls.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_url, url) for url in urls]
        for _ in as_completed(futures):
            pass

if __name__ == "__main__":
    main()
