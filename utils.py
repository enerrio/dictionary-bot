import requests
from requests.exceptions import HTTPError


def get_webcontent(url: str) -> requests.models.Response:
    """Get the web contents from a given URL

    Returns:
        requests.models.Response: Response to GET containing web contents
    """
    try:
        page = requests.get(url)
        page.raise_for_status()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")
    return page
