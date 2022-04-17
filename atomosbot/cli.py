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

# flaskオブジェクトを作成
app = Flask(__name__)

# 各クライアントライブラリのインスタンスを作成
line_bot_api = LineBotApi(os.environ["CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])


@app.route("/callback", methods=["POST"])
def callback() -> str:
    """Webhookからのリクエストの正当性をチェックし、handlerに処理を渡す

    /callbackにPOSTリクエストがあった場合、それが正当なLINEBotのWebhookからの
    リクエストであるかどうかをチェックし、署名が正当であればhandlerに処理を渡します。

    Returns
    -------
    str
        例外が発生しなかった場合は"OK"を返します。
    """

    # リクエストヘッダーから署名検証のための値を取得
    signature = request.headers["X-Line-Signature"]

    # リクエストボディの取得
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        # 署名を検証し、問題なければhandleに定義している関数を呼び出す
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warn("Invalid Signature.")
        abort(400)

    # 例外が発生せず、handlerの処理が終了すればOK
    return "OK"


# addメソッドの引数にはイベントのモデルを入れる
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event) -> None:
    """返信メッセージを作成

    Parameters
    ----------
    Any
        ユーザーからのメッセージイベント
    """
    try:
        # クラスオブジェクトを作成
        forecast = ForecastAtomosPhenom(address=event.message.text, duration=30)

        # メッセージを作成
        messages = forecast.make_linebot_messages()
    except Exception:
        # 例外が発生した場合はプロットを作成せず代わりのテキストを返す
        messages = TextSendMessage(text="都市名もしくは住所を入力してください。")

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
