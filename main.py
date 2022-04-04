import os
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 環境変数取得
MY_CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
MY_CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
USER_ID = os.environ["USER_ID"]

line_bot_api = LineBotApi(MY_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(MY_CHANNEL_SECRET)


@app.route("/callback", methods=["POST"])
def callback():
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
def handle_message(event):
    if "気圧" in event.message.text:
        replyText = "登録しました"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=replyText))

    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text=event.message.text)
    )


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage="Usage: python " + __file__ + " [--port <port>] [--help]"
    )
    # Herokuは環境変数PORTのポートで起動したWeb Appの起動を待ち受けるため、そのポート番号でApp起動する
    arg_parser.add_argument(
        "-p", "--port", type=int, default=int(os.environ.get("PORT", 8000)), help="port"
    )
    arg_parser.add_argument("-d", "--debug", default=False, help="debug")
    arg_parser.add_argument("--host", default="0.0.0.0", help="host")
    options = arg_parser.parse_args()

    app.run(debug=options.debug, host=options.host, port=options.port)
