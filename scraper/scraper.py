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
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

DECADE_COUNTS = {
    1930: 5000,
    1940: 5000,
    1950: 5000,
    1960: 5000,
    1970: 10000,
    1980: 10000,
    1990: 20000,
    2000: 20000,
    2010: 20000,
    2020: 20000,
}


def get_page_info(max_pages: int, start_page: int):
    """
    https://letterboxd.com/films/popular/
    Goes to the link above and retrieves information about the movies there. 
    NOTE: Does not get movie poster URL's. For that, you need to visit the main page of each movie. This will be done in 'get_poster_urls'.
    
    """

    film_dict = {}

    for i in tqdm(range(max_pages)):
        start = time.time()
        logger.info(f"=================== Reading page {i+1} =================== ")
        logger.info(f"https://letterboxd.com/films/ajax/popular/page/{start_page + i+1}/?esiAllowFilters=true")
        try:
            page_url = f"https://letterboxd.com/films/ajax/popular/page/{start_page + i+1}/?esiAllowFilters=true"
            resp = requests.get(page_url, headers=HEADERS)
            soup = BeautifulSoup(resp.text, features="html.parser")
                    
            data = soup.select("li.posteritem")
            for data_block in data:
                block = data_block.find("div", class_="react-component")

                if block:
                    metadata = {
                        "title": block.get("data-item-full-display-name"),
                        "slug": block.get("data-item-slug"),
                        "film_id": block.get("data-film-id"),
                        "details": block.get("data-details-endpoint"),
                        "poster_url": block.get("data-poster-url"),
                        "page_link": block.get("data-item-link"),
                        "rating": data_block.get("data-average-rating")
                    }
                else:
                    logger.error(f"Data block could not be created")
                    continue

                # print(f"https://letterboxd.com/film/{metadata['slug']}/")
                temp_metadata = get_detailed_info(f"https://letterboxd.com/film/{metadata['slug']}/")

                if temp_metadata.get("Error"):
                    # print(f"Error encountered for movie {metadata['slug']}")
                    logger.error(f"Error encountered for movie {metadata['slug']}. Error: {temp_metadata.get('Error')}")
                    logger.error(f"https://letterboxd.com/film/{metadata['slug']}/")
                    continue

                for key, value in temp_metadata.items():
                    metadata[key] = value

                film_dict[f"https://letterboxd.com/film/{metadata['slug']}/"] = metadata # type: ignore
                logger.info(f"Succesfull - https://letterboxd.com/film/{metadata['slug']}/")
                time.sleep(0.2)
            end = time.time()
            log_time(start, end, logger)

            if i%250 == 0:
                with open("data/movie_info_checkpoint.json", "w") as f:
                    json.dump(film_dict, f, indent=2)

            time.sleep(1)

        except Exception as e:
            logger.error(e)
            logger.error(f"Got error in page {i}")
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

    raw = script.string.strip() # type: ignore
    clean = raw.replace("/* <![CDATA[ */", "").replace("/* ]]> */", "").strip()
    try:
        data = json.loads(clean)
    except Exception as e:
        return {"Error": f"JSON parse failed: {e}"}

    #if not data.get("aggregateRating"): # If there is no rating, it means to movie has not been released yet.
    #    return {"Error": "Not released yet"}

    metadata = {
            "posterUrl": data.get("image"),
            "director": data.get("director"),
            "productionCompany": data.get("productionCompany"),
            "genre": data.get("genre"),
            "countryOfOrigin": data.get("countryOfOrigin"),
            "aggregateRating": data.get("agregateRating"),
        }

    return metadata


def get_images(film_dict: dict):
    """
    Takes the film_dict as an input, extracts the poster url and saves it to data/posters/ as {slug}.jpg
    """
    start = time.time()
    for item, key in tqdm(film_dict.items()):
        poster_url = key.get("posterUrl")
        movie_name = key.get("slug")

        try:
            img_data = requests.get(poster_url).content
            with open(f'data/posters/{movie_name}.jpg', 'wb') as handler:
                handler.write(img_data)
            logger.info(f"Image download/upload succesfull - {movie_name}")
        except Exception as e:
            logger.error(f"Error while downloading/uploading the image. f{e}")
            continue
    end = time.time()
    log_time(start, end, logger)
        

def log_time(start, end, logger):
    elapsed = end - start
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    logger.info(f"{minutes}m {seconds:02d}s")


if __name__ == "__main__":
    logger.info("Starting scraper")
    film_dict = get_page_info(max_pages=2000, start_page=2000)
    with open("data/movie_info.json", "w") as f:
        json.dump(film_dict, f, indent=2)

    with open("data/movie_info.json") as f:
            data = json.load(f)

    get_images(data)