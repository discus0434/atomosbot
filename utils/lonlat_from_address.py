from typing import Tuple
import requests
from bs4 import BeautifulSoup


def get_lon_lat_from_address(address: str) -> Tuple[str, str]:
    """渡したアドレスの緯度・経度を返すメソッド

    Parameters
    ----------
    address : str
        任意のアドレス

    Returns
    -------
    Tuple[str, str]
        経度・緯度

    Examples
    --------
    >>> get_lon_lat_from_address('東京都文京区本郷7-3-1')
    ['35.712056', '139.762775']
    """
    url = "http://www.geocoding.jp/api/"

    payload = {"q": address}
    html = requests.get(url, params=payload)
    soup = BeautifulSoup(html.content, "html.parser")
    if soup.find("error"):
        raise ValueError(f"Invalid address submitted. {address}")
    longitude = soup.find("lng").string
    latitude = soup.find("lat").string

    return longitude, latitude
