from typing import Dict, Any
import requests


def get_api_data(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """APIを叩く際使用するWrapper関数

    Args:
        url (str): URL
        params (Dict[str, Any]): APIに渡すパラメータ

    Returns:
        Dict[str, Any]: 取得したjsonファイル
    """
    url = url
    params = params

    return requests.get(url, params=params).json()
