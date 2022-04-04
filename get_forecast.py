import os
import json
import requests
import datetime
from datetime import datetime as dt

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import plotly.graph_objects as go
from dotenv import load_dotenv


class ForecastAirPressure:
    def __init__(self, location="MITAKA"):

        load_dotenv(override=True)

        self.channel_access_token = os.environ["CHANNEL_ACCESS_TOKEN"]
        self.channel_secret = os.environ["CHANNEL_SECRET"]
        self.user_id = os.environ["USER_ID"]
        self.openweather_api_key = os.environ["OPENWEATHER_API_KEY"]
        self.gyazo_api_key = os.environ["GYAZO_API_KEY"]

        self.location = location
        self.res = self.timestamp_2_datetime(self.get_forcast())

        self.cmap = {
            "Clear": "orange",
            "Clouds": "grey",
            "Rain": "skyblue",
        }

    def get_lon_lat(self):
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": self.location, "appid": self.openweather_api_key, "lang": "ja"}
        result = self.get_api_data(url=url, params=params)

        return result["coord"]["lon"], result["coord"]["lat"]

    def get_forcast(self):
        url = "http://api.openweathermap.org/data/2.5/onecall"
        lon, lat = self.get_lon_lat()
        params = {
            "lon": lon,
            "lat": lat,
            "units": "metric",
            "exclude": "daily,minutely",
            "appid": self.openweather_api_key,
            "lang": "ja",
        }
        result = self.get_api_data(url=url, params=params)

        return result

    def plot_forcast(self):
        dates = [
            self.res["hourly"][idx]["dt"] for idx in range(len(self.res["hourly"]))
        ]
        air_pressure = [
            self.res["hourly"][idx]["pressure"]
            for idx in range(len(self.res["hourly"]))
        ]
        weather = [
            self.res["hourly"][idx]["weather"][0]["main"]
            for idx in range(len(self.res["hourly"]))
        ]
        weather_icon = [
            self.res["hourly"][idx]["weather"][0]["icon"]
            for idx in range(len(self.res["hourly"]))
        ]

        diff = self.detect_where_to_cautious(dates=dates, air_pressure=air_pressure)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=air_pressure, mode="lines", name="気圧"))
        fig.add_trace(
            go.Bar(
                x=dates,
                y=[1050] * len(dates),
                name="天気",
                marker={"color": [self.cmap[w] for w in weather], "opacity": 0.4},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=list(diff.keys()),
                y=[elm[0] for elm in diff.values()],
                mode="markers",
                marker=go.scatter.Marker(
                    size=[elm[1] * 20 for elm in diff.values()],
                    color=[elm[1] for elm in diff.values()],
                    cmax=5,
                    cmin=1,
                    opacity=0.3,
                    colorscale="jet",
                ),
                name="要警戒",
            )
        )
        fig.update_layout(
            dict(
                title=f"{self.location}の予報",
                yaxis={"range": (min(air_pressure) - 1, max(air_pressure) + 1)},
            )
        )
        for idx, icon in enumerate(weather_icon):
            fig.add_layout_image(
                dict(
                    source=f"https://openweathermap.org/img/wn/{icon}@2x.png",
                    xref="paper",
                    yref="paper",
                    x=idx / 47.5 - 0.01,
                    y=1.1,
                    sizex=0.03,
                    sizey=0.08,
                    sizing="stretch",
                    opacity=1,
                )
            )

        return fig

    @staticmethod
    def get_api_data(url, params):
        url = url
        params = params

        return requests.get(url, params=params).json()

    @staticmethod
    def timestamp_2_datetime(res):
        for idx in range(len(res["hourly"])):
            res["hourly"][idx]["dt"] = dt.fromtimestamp(
                res["hourly"][idx]["dt"]
            ).strftime("%m-%d %H")

        return res

    @staticmethod
    def detect_where_to_cautious(dates, air_pressure):
        diff = {}
        for idx in range(len(air_pressure) - 5):
            if abs(air_pressure[idx + 5] - air_pressure[idx]) > 2:
                inc = 1
                while (idx + 5 + inc < len(air_pressure)) and (
                    abs(air_pressure[idx + 5 + inc] - air_pressure[idx])
                    >= abs(air_pressure[idx + 5] - air_pressure[idx])
                ):
                    inc += 1

                if dates[idx + 1 + inc // 2] not in diff.keys():
                    diff[dates[idx + 1 + inc // 2]] = [
                        air_pressure[idx + 1 + inc // 2],
                        abs(air_pressure[idx + 5] - air_pressure[idx]) + 1,
                    ]

        return diff


if __name__ == "__main__":
    forcast_air_pressure = ForecastAirPressure()

    app = Flask(__name__)
    line_bot_api = LineBotApi(forcast_air_pressure.channel_access_token)

    forcast_air_pressure.plot_forcast().write_image(
        "air_pressure.jpeg", width=1700, height=700
    )

    with open("air_pressure.jpeg", "rb") as f:
        files = {"imagedata": f.read()}

        response = requests.request(
            method="post",
            url="https://upload.gyazo.com/api/upload",
            headers={"Authorization": f"Bearer {forcast_air_pressure.gyazo_api_key}"},
            files=files,
        )

    image_message = ImageSendMessage(
        original_content_url=json.loads(response.text)["url"],
        preview_image_url=json.loads(response.text)["thumb_url"],
    )
    line_bot_api.push_message(forcast_air_pressure.user_id, messages=image_message)
