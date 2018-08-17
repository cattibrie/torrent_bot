import configparser
import logging
import os
import requests


class storeConfig:
    def __init__(self):
        self.token = None
        self.users = []
        self.path = None

    def getConfig(self):
        config = configparser.ConfigParser()
        config.read("configfile.ini")
        if "token" not in config["DEFAULT"]:
            logging.error("There is no Bot token")
            return
        if "store_path" not in config["DEFAULT"]:
            logging.error("Define path where to store torrent files")
            return
        self.token = config["DEFAULT"]["token"]
        self.path = config["DEFAULT"]["store_path"]
        for user in config["USERNAME"]:
            self.users.append(config["USERNAME"][user])


STORE = storeConfig()


def make_request(endpoint, payload=None, method="get"):
    '''
    Make request to Telegram Bot API
    Input: endpoint, payload and method
    Returns value of the result field of the response or None
    '''
    try:
        if method == "get":
            res = requests.get(url=endpoint, params=payload)
        elif method == "post":
            res = requests.post(url=endpoint, data=payload)
        if res.status_code != 200:
            # Log status code if not 200
            logging.error("Status code {}; reson: {}".format(res.status_code, res.reason))
            return
        response = res.json()
        if response["ok"]:
            return response["result"] if method == "get" else None
        else:
            # log description if "ok" field of the response is false
            logging.error(response['description'])
    except Exception:
        logging.exception("error in request_update")


def request_update(offset):
    '''
    Make GetUpdate request to Telegram Bot API
    Returns array of updates of filed result of the Update object
    Elements of array are dicts
    '''
    endpoint = "https://api.telegram.org/bot{}/getUpdates".format(STORE.token)
    payload = {"timeout": 60}
    if offset:
        payload['offset'] = offset
    return make_request(endpoint, payload)


def send_msg(message, chat_id):
    '''
    Make sendMessage request to Telegram Bot API
    Sends message to chat with chat_id
    '''
    endpoint = "https://api.telegram.org/bot{}/sendMessage".format(STORE.token)
    payload = {"chat_id": chat_id, "text": message}
    make_request(endpoint, payload, "post")


def getFile(file_id):
    '''
    Make getFile request to Telegram Bot API
    Returns value of the result field of File object or None
    '''
    endpoint = "https://api.telegram.org/bot{}/getFile".format(STORE.token)
    payload = {"file_id": file_id}
    return make_request(endpoint, payload)


def new_name(doc_name):
    '''
    Formats the name of the file
    '''
    name_strip = doc_name.strip()
    for old in [" ", "..", "/"]:
        new_name = name_strip.replace(old, "")
    return new_name


def torrentExists(doc_name, doc_size):
    '''
    Check existanse of the file with name "doc_name" and size "doc_size"
    '''
    checkpath = "{}/{}".format(STORE.path, doc_name)
    if os.path.isfile(checkpath):
        if os.path.getsize(checkpath) == doc_size:
            return (True, "")
        else:
            new_name = doc_name + "_new"
            return (False, new_name)
    return (False, doc_name)


def download_file(file_id, doc_name, doc_size, chat_id):
    '''
    '''
    # Check if file doc_name exists
    ok, doc_name = torrentExists(doc_name, doc_size)
    logging.info("ok: {}, doc_name: {}".format(ok, doc_name))
    if ok:
        send_msg("This torrent file exists", chat_id)
        return
    file_obj = getFile(file_id)
    logging.info("Got file id")
    if not file_obj:
        return
    file_path = file_obj["file_path"]
    if not file_path:
        return
    endpoint = "https://api.telegram.org/file/bot{}/{}".format(STORE.token, file_path)
    store_path = "{}/{}".format(STORE.path, doc_name)
    with open(store_path, "wb") as f:
        res = requests.get(url=endpoint)
        f.write(res.content)
        res = None
    send_msg("file downloaded", chat_id)


def parse_update(result):
    for update in result:
        user = update["message"]["from"]["username"]
        chat_id = update['message']['chat']['id']
        if user not in STORE.users:
            send_msg("User with username {} is not allowed to send files".format(user), chat_id)
            logging.error("User with username {} is not allowed to send files".format(user))
            return
        if "document" in update["message"]:
            doc_name = update["message"]["document"]["file_name"]
            doc_size = update["message"]["document"]["file_size"]
            if doc_size <= 20*1024*1024 and doc_name.endswith(".torrent"):
                send_msg("you sent torrent file", chat_id)
                file_id = update["message"]["document"]["file_id"]
                download_file(file_id, new_name(doc_name), doc_size, chat_id)


def look_for_update():
    '''
    Function that monitors for updates and sends messages in chat
    '''
    offset = None
    STORE.getConfig()
    while True:
        result = request_update(offset)
        if result:
            logging.info(result)
            offset = result[len(result) - 1]["update_id"] + 1
            parse_update(result)


def main():
    logging.basicConfig(filename='torrent_bot.log', level=logging.DEBUG)
    look_for_update()
