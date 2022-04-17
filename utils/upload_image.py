import requests


def upload_image_to_gyazo(save_path: str, api_key: str) -> requests.Response:
    """画像をgyazoにアップロードし、レスポンスを取得

    Parameters
    ----------
    save_path : str
        画像の保存先
    api_key : str
        画像アップロードサービスのAPIキー

    Returns
    -------
    requests.Response
        画像がアップロードされたURLの情報を含むレスポンス
    """
    # 作成したプロットをgyazoにアップロード
    with open(save_path, "rb") as f:
        files = {"imagedata": f.read()}

        res = requests.request(
            method="post",
            url="https://upload.gyazo.com/api/upload",
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
        )

    return res
