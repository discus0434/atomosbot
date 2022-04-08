"""気象情報を取得し、データを加工してLINEに送信"""
import os
from pathlib import Path
import sys
import json
from typing import Any, Dict, List
import datetime
from datetime import datetime as dt, timedelta

from linebot import LineBotApi
from linebot.models import TextSendMessage, ImageSendMessage
import plotly.graph_objects as go

sys.path.append(Path(__file__).resolve().parents[1].as_posix())

from utils.api_wrapper import get_api_data
from utils.lonlat_from_address import get_lon_lat_from_address
from utils.upload_image import upload_image_to_gyazo

# ローカルでのみ使用する環境変数の設定
try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except Exception:
    pass


class ForecastAtomosPhenom:
    def __init__(self, address: str = "三鷹市", duration: int = 30):
        """コンストラクタ

        Args:
            address (str, optional): 気象情報を取得する地名
                Defaults to "三鷹市".
            duration (int, optional): 気象情報を設定した時間(<48時間後)まで
                表示する Defaults to 30.
        """
        # タイムゾーンを指定
        self.jst = datetime.timezone(datetime.timedelta(hours=9), "JST")

        # 環境変数
        self.user_id = os.environ["USER_ID"]
        self.openweather_api_key = os.environ["OPENWEATHER_API_KEY"]
        self.gyazo_api_key = os.environ["GYAZO_API_KEY"]

        # プロットの出力先を指定
        self.save_plot_path = "plot.jpeg"

        # 取得対象を指定
        self.address = address
        self.duration = duration

        # 天気予報を取得し、タイムスタンプで取得された日時をdatetime型に変換
        self.res = self.convert_timestamp_into_datetime(res=self.get_forecast())

        # 天気ごとの表示色を指定
        self.cmap = {
            "Clear": "orange",
            "Clouds": "grey",
            "Rain": "skyblue",
        }

    def make_linebot_messages(self) -> List[Any]:
        """Botが送信するメッセージ全体を作成

        Returns:
            List[Any]: Botが送信するメッセージで、画像とテキストを含む
        """
        # 取得したデータから必要な情報を抽出
        r = self.res["hourly"]
        # 気温
        self.temp = [r[idx]["temp"] for idx in range(self.duration)]
        # 日時
        self.dates = [r[idx]["dt"] for idx in range(self.duration)]
        # 気圧
        self.atomos_phenomena = [r[idx]["pressure"] for idx in range(self.duration)]
        # 天気
        self.weather = [r[idx]["weather"][0]["main"] for idx in range(self.duration)]

        # 気圧が変動する時間帯を算出
        self.alarming_dates = self.calc_when_to_cautious_pressure_change(
            dates=self.dates, atomos_phenomena=self.atomos_phenomena
        )

        # メッセージの画像部分（プロット）を作成・保存
        self.make_image_message()

        # 作成したプロットをgyazoにアップロード
        response = upload_image_to_gyazo(
            save_path=self.save_plot_path,
            api_key=self.gyazo_api_key,
        )

        # メッセージを作成
        messages = [
            ImageSendMessage(
                original_content_url=json.loads(response.text)["url"],
                preview_image_url=json.loads(response.text)["thumb_url"],
            ),
            TextSendMessage(text=f"{self.make_text_message()}"),
        ]

        return messages

    def get_forecast(self) -> Dict[str, Any]:
        """天気予報をOpenWeathermap.orgから取得

        Returns:
            res (Dict[str, Any]): 取得したjsonファイル
        """
        # URL
        url = "http://api.openweathermap.org/data/2.5/onecall"

        # 都市名を緯度・経度に変換
        lon, lat = get_lon_lat_from_address(address=self.address)

        params = {
            # 経度
            "lon": lon,
            # 緯度
            "lat": lat,
            # 気温を摂氏で取得
            "units": "metric",
            # 必要のない情報をexclude
            "exclude": "daily,minutely",
            # APIキー
            "appid": self.openweather_api_key,
            # 取得情報の一部を日本語化
            "lang": "ja",
        }

        # データの取得
        res = get_api_data(url=url, params=params)

        return res

    def make_image_message(self) -> None:
        """取得した予報データをPlotlyでプロットし、jpegとして保存

        取得時刻から約{duration}時間後までの毎時の気温・気圧・天気と、
        気圧が変動する時間帯を可視化し、LineBotが送信するメッセージの画像部分として
        保存する
        """
        # プロット
        fig = go.Figure()

        # 気圧の折れ線グラフ
        fig.add_trace(
            go.Scatter(x=self.dates, y=self.atomos_phenomena, mode="lines", name="気圧")
        )

        # 気温の折れ線グラフ
        fig.add_trace(
            go.Scatter(x=self.dates, y=self.temp, mode="lines", name="気温", yaxis="y2")
        )

        # 天気の棒グラフ（実質的には背景色を天気で変化させるためのグラフ）
        fig.add_trace(
            go.Bar(
                x=self.dates,
                y=[1050] * len(self.dates),
                name="天気",
                marker={"color": [self.cmap[w] for w in self.weather], "opacity": 0.4},
            )
        )

        # 要警戒時間帯の棒グラフ（実質的には背景色を要警戒か否かで変化させるためのグラフ）
        fig.add_trace(
            go.Bar(
                x=self.alarming_dates,
                y=[1050] * len(self.dates),
                name="要警戒の時間帯",
                marker_pattern_shape="\\",
                marker=dict(color="red"),
                opacity=0.2,
            )
        )

        # グラフの装飾
        fig.update_layout(
            dict(
                font=dict(family="Kiwi Maru", size=20),
                title=f"今日から明日にかけての{self.address}の気象情報",
                width=1300,
                height=1000,
                xaxis=dict(
                    title="日時",
                    type="date",
                    tickformat="%-m/%-d %-H時",
                    tickfont=dict(size=18),
                ),
                yaxis=dict(
                    title="気圧[hPa]",
                    range=(
                        min(self.atomos_phenomena) - 1,
                        max(self.atomos_phenomena) + 1,
                    ),
                    tickfont=dict(size=18),
                ),
                yaxis2=dict(
                    title="気温[℃]",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    tickfont=dict(size=18),
                ),
            )
        )

        # プロットをjpegで保存
        fig.write_image(self.save_plot_path, width=1300, height=1000)

        return None

    def make_text_message(self) -> str:
        """LineBotが送信するメッセージのうち、テキスト部分を作成

        最高・最低気温、気圧変動の時間帯をテキストでも表示する

        Returns:
            str: LineBotが送信するメッセージのテキスト部分
        """

        # 気圧変動が大きい時間のリストの中で値が連続しているものをグループ化し、
        # テキストとして表示しやすくする
        alarming_list = []

        # 気圧変動が大きい時間のリストでループを回す
        for idx, date in enumerate(self.alarming_dates):

            # ループ変数が始端か終端の要素の場合は別処理を行う
            if idx == 0:
                continuous = [date]
                continue
            elif idx == len(self.alarming_dates) - 1:
                if len(continuous) > 1:
                    alarming_list.append([continuous[0], continuous[-1]])
                    continue

            # 連続の有無を判別
            is_continuous = self._validate(
                cur=self.alarming_dates[idx], pre=self.alarming_dates[idx - 1]
            )

            # 連続している場合、一時的にリストに加えて続行
            if is_continuous:
                continuous.append(date)
            # 連続していない場合、現時点での一時リストの始端と終端を連続した時間帯と
            # みなして保存し、現在のループ変数を要素として一時リストを初期化
            else:
                if len(continuous) > 1:
                    alarming_list.append([continuous[0], continuous[-1]])
                continuous = [date]

        # 要素の型をdatetime型からstr型に変更
        alarm_list = [
            list(map(lambda x: dt.strftime(x, "%d日 %-H時"), duration))
            for duration in alarming_list
        ]

        # メッセージのテキスト部分を記述
        alarm_text = (
            f"{(dt.strftime(datetime.datetime.now(self.jst), '%Y年%-m月%-d日(%a)'))}\n"
            + f"{self.address}の気象情報です。\n\n"
            + f"今度24時間の最高気温は{max(self.temp[:24])}度、\n"
            + f"最低気温は{min(self.temp[:24])}度です。\n\n"
            "気圧が変動するのは以下の時間帯です。\n\n"
            + "".join(
                "から".join(
                    list(
                        map(
                            lambda x: x.replace(x[:4], "今日")
                            if alarm_list[0][0][:4] == x[:4]
                            else x.replace(x[:4], "明日"),
                            li,
                        )
                    )
                )
                + "\n"
                for li in alarm_list
            )
            + "詳細は画像をご覧ください。"
        )

        return alarm_text

    @staticmethod
    def _validate(cur: datetime.datetime, pre: datetime.datetime) -> bool:
        """今の値が前の値と連続しているかどうか判別

        Args:
            cur (datetime.datetime): 現在の値
            pre (datetime.datetime): 1つ前のインデックスの値

        Returns:
            bool: 連続しているかどうか
        """
        return cur == (pre + datetime.timedelta(seconds=3600))

    @staticmethod
    def convert_timestamp_into_datetime(res: Dict[str, Any]) -> Dict[str, Any]:
        """タイムスタンプで表現された日時をdatetime型に変換

        OpenWeathermap.orgから取得したデータの日時がタイムスタンプで得られるため、
        変換が必要となる

        Args:
            res (Dict[str, Any]): 取得したjsonファイル

        Returns:
            Dict[str, Any]: 日時の型を変換したjsonファイル
        """
        for idx in range(len(res["hourly"])):
            res["hourly"][idx]["dt"] = dt.fromtimestamp(
                res["hourly"][idx]["dt"]
            ) + timedelta(hours=9)

        return res

    @staticmethod
    def calc_when_to_cautious_pressure_change(
        dates: List[datetime.datetime], atomos_phenomena: List[int]
    ) -> List[datetime.datetime]:
        """気圧が大きめに変動する時間帯を算出

        ある日時とその3時間後の気圧差を比較して2hPa以上の差がある場合、その時間帯を
        ピックアップし、更にその1時間後, 2時間後,...の気圧変動も確認して気圧変動が
        一方向に大きい時間帯がどこからどこまで続いているのか算出する

        Args:
            dates (List[datetime.datetime]): 取得した気象情報の日時データ
            atomos_phenomena (List[int]): 取得した気象情報の気圧データ

        Returns:
            List[datetime.datetime]: 気圧が大きめに変動する時間のリスト
        """
        alarming = []
        for idx in range(len(atomos_phenomena) - 3):
            if abs(atomos_phenomena[idx + 3] - atomos_phenomena[idx]) > 2:
                inc = 1
                while (idx + 3 + inc < len(atomos_phenomena)) and (
                    abs(atomos_phenomena[idx + 3 + inc] - atomos_phenomena[idx])
                    > abs(atomos_phenomena[idx + 3 + inc - 1] - atomos_phenomena[idx])
                ):
                    inc += 1

                alarming.append([dates[i] for i in range(idx, idx + 3 + inc)])

        alarming_dates = sorted(
            list(set([item for sublist in alarming for item in sublist]))
        )

        return alarming_dates


if __name__ == "__main__":
    # 気象情報を取得
    forecast = ForecastAtomosPhenom()

    # メッセージを作成
    messages = forecast.make_linebot_messages()

    # メッセージを送信
    line_bot_api = LineBotApi(os.environ["CHANNEL_ACCESS_TOKEN"])
    line_bot_api.push_message(forecast.user_id, messages=messages)
