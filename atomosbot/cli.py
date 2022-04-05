"""LINE Botの基幹となる処理"""
import os
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from forecast_atomos_phenom import ForecastAtomosPhenom

# ローカルでのみ使用する環境変数の設定
try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except Exception:
    pass

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ["CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])


@app.route("/callback", methods=["POST"])
def callback() -> str:
    """Webhookからのリクエストの正当性をチェックし、handlerに応答処理を移譲する"""

    signature = request.headers["X-Line-Signature"]

    # get request body
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warn("Invalid Signature.")
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event) -> None:
    """返信メッセージを作成

    Args:
        event (Any): ユーザーからのメッセージイベント
    """
    try:
        # 初期化
        forecast = ForecastAtomosPhenom(address=event.message.text)

        # メッセージを作成
        messages = forecast.make_linebot_messages()
    except Exception:
        # 例外が発生した場合はプロットを作成せず代わりのテキストを返す
        messages = TextSendMessage(text="都市名をローマ字で入力してください。")

    line_bot_api.reply_message(event.reply_token, messages=messages)


def main() -> None:
    # Usage Messageの作成
    arg_parser = ArgumentParser(
        usage="Usage: python " + __file__ + " [--port <port>] [--help]"
    )

    # 環境変数PORTのと同じポート番号でAppを起動する
    arg_parser.add_argument(
        "-p", "--port", type=int, default=int(os.environ.get("PORT", 8000)), help="port"
    )
    arg_parser.add_argument("-d", "--debug", default=False, help="debug")
    arg_parser.add_argument("--host", default="0.0.0.0", help="host")
    options = arg_parser.parse_args()
    app.run(debug=options.debug, host=options.host, port=options.port)


if __name__ == "__main__":
    main()
