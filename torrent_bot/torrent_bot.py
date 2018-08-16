import logging
import os
import requests


# TOKEN fot Telegram bot
TOKEN = os.getenv('TOKEN')


def make_request(endpoint, payload=None, method="get"):
        '''
        Make request to Telegram Bot API
        Input: endpoint, payload and method
        Returns value of the result field of the response or None
        '''
        try:
            if method == "get":
                res = requests.get(url=endpoint, params=payload)
            else:
                res = requests.post(url=endpoint, data=payload)
            if res.status_code != 200:
                logging.error(res.status_code)
                return
            response = res.json()
            if response["ok"]:
                return response["result"] if method == "get" else None
            else:
                # log errors
                logging.error(response['description'])
                return
        except Exception:
            logging.exception("error in request_update")


def request_update(offset):
    '''
    Make GetUpdate request to Telegram Bot API
    Returns array of updates of filed result of the Update object
    Elements of array are dicts
    '''
    endpoint = "https://api.telegram.org/bot{}/getUpdates".format(TOKEN)
    payload = {"timeout": 60}
    if offset:
        payload['offset'] = offset
    return make_request(endpoint, payload)


def send_msg(message):
    '''
    Make sendMessage request to Telegram Bot API
    Sends message to chat with chat_id
    Returns None
    '''
    endpoint = "https://api.telegram.org/bot{}/sendMessage".format(TOKEN)
    payload = {"chat_id": -282900057, "text": message}
    return make_request(endpoint, payload, "post")


def getFile(file_id):
    '''
    Make getFile request to Telegram Bot API
    Returns value of the result field of File object or None
    '''
    endpoint = "https://api.telegram.org/bot{}/getFile".format(TOKEN)
    payload = {"file_id": file_id}
    return make_request(endpoint, payload)


def download_file(file_id, doc_name):
    '''
    '''
    file_obj = getFile(file_id)
    file_path = file_obj["file_path"] if file_obj else None
    if file_path:
        endpoint = "https://api.telegram.org/file/bot{}/{}".format(TOKEN, file_path)
        with open(doc_name, "wb") as f:
            res = requests.get(url=endpoint)
            file_cont = res.content
            f.write(file_cont)
        send_msg("file downloaded")


def parse_update(result):
    for update in result:
        if "document" in update["message"]:
            doc_name = update["message"]["document"]["file_name"]
            doc_size = update["message"]["document"]["file_size"]
            name_len = len(doc_name)
            if doc_size <= 20971520 and name_len >= 8 and doc_name[name_len - 8:] == ".torrent":
                send_msg("you sent torrent file")
                file_id = update["message"]["document"]["file_id"]
                download_file(file_id, doc_name)


def look_for_update():
    '''
    Function that monitors for updates and sends messages in chat
    '''
    offset = None
    send_msg("Hello Kate")
    while True:
        result = request_update(offset)
        if result:
            logging.info(len(result))
            logging.info(result)
            offset = result[len(result) - 1]["update_id"] + 1
            parse_update(result)


def main():
    logging.basicConfig(filename='torrent_bot.log', level=logging.DEBUG)
    look_for_update()
