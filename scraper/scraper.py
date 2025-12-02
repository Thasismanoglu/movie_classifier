from bs4 import BeautifulSoup
import requests
import json
import typing
import time
import logging
from tqdm import tqdm

logging.basicConfig(
    filename="logs/scraper.log",
    level=logging.INFO,
    filemode="w",
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def get_page_info(max_pages: int):
    """
    https://letterboxd.com/films/popular/this/week/
    Goes to the link above and retrieves information about the movies there. 
    NOTE: Does not get movie poster URL's. For that, you need to visit the main page of each movie. This will be done in 'get_poster_urls'.
    
    """

    film_dict = {}

    for i in tqdm(range(max_pages)):
        start = time.time()
        logger.info(f"=================== Reading page {i+1} ===================")
        try:
            page_url = f"https://letterboxd.com/films/ajax/popular/this/week/page/{i+1}/?esiAllowFilters=true"
            resp = requests.get(page_url, headers=HEADERS)
            soup = BeautifulSoup(resp.text, features="html.parser")
                    
            data = soup.select("li.posteritem")
            for data_block in data:
                block = data_block.find("div", class_="react-component")

                metadata = {
                    "title": block.get("data-item-full-display-name"),
                    "slug": block.get("data-item-slug"),
                    "film_id": block.get("data-film-id"),
                    "details": block.get("data-details-endpoint"),
                    "poster_url": block.get("data-poster-url"),
                    "page_link": block.get("data-item-link"),
                    "rating": data_block.get("data-average-rating")
                }

                # print(f"https://letterboxd.com/film/{metadata['slug']}/")
                temp_metadata = get_detailed_info(f"https://letterboxd.com/film/{metadata['slug']}/")

                if temp_metadata.get("Error"):
                    # print(f"Error encountered for movie {metadata['slug']}")
                    logger.error(f"Error encountered for movie {metadata['slug']}. Error: {temp_metadata.get('Error')}")
                    continue

                for key, value in temp_metadata.items():
                    metadata[key] = value

                film_dict[f"https://letterboxd.com/film/{metadata['slug']}/"] = metadata # type: ignore
                logger.info(f"Succesfull - https://letterboxd.com/film/{metadata['slug']}/")
                time.sleep(0.2)
            end = time.time()

            elapsed = end - start
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)

            logger.info(f"{minutes}m {seconds:02d}s")
            time.sleep(1)
        except Exception as e:
            logger.error(e)
            with open("data/movie_info.json", "w") as f:
                json.dump(film_dict, f, indent=2)

    return film_dict


def get_detailed_info(movie_url: str, debug=False):
    """
    Gets detailed info of a movie
    """
    resp = requests.get(movie_url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, features="html.parser")

    script = soup.find("script", {"type": "application/ld+json"})
    
    if debug:
        print(f"Soup: {soup}")
        print(f"Script: {script}")

    raw = script.string.strip()
    clean = raw.replace("/* <![CDATA[ */", "").replace("/* ]]> */", "").strip()
    data = json.loads(clean)

    if not data.get("aggregateRating"): # If there is no rating, it means to movie has not been released yet.
        return {"Error": "Not released yet"}

    metadata = {
            "posterUrl": data["image"],
            "director": data["director"],
            "productionCompany": data["productionCompany"],
            "genre": data["genre"],
            "countryOfOrigin": data["countryOfOrigin"],
            "aggregateRating": data["aggregateRating"],
        }

    return metadata


if __name__ == "__main__":
    logger.info("Starting scraper")
    film_dict = get_page_info(max_pages=2)
    with open("data/movie_info.json", "w") as f:
        json.dump(film_dict, f, indent=2)

