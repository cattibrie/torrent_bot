import configparser
import hashlib
import logging
import os
import requests


class Storemd5hash:
    def __init__(self, dir_path):
        self.md5hash = set()
        self.count_files_md5hash_indir(dir_path)

    def count_files_md5hash_indir(self, dir_path):
        """
        Function that counts md5 hash for all files in directory
        with given "dir_path"
        """
        for file_name in os.listdir(dir_path):
            file_path = "{}/{}".format(dir_path, file_name)
            self.md5hash.add(count_md5hash_file(file_path))

    def add_md5hash(self, md5hash):
        self.md5hash.add(md5hash)


def count_md5hash_file(file_path):
    """
    Function counts md5 hash of file where input is file_path
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def count_md5hash_bytes(byte_flow):
    """
    Function counts md5 hash of file where input is file in bytes
    """
    hash_md5 = hashlib.md5()
    hash_md5.update(byte_flow)
    return hash_md5.hexdigest()


class TorrentBot:
    def __init__(self):
        self.token = None
        self.path = None
        self.users = set()
        self.chat_id = None
        self.offset = None
        self.getConfig()
        self.md5hash_store = Storemd5hash(self.path)

    def getConfig(self):
        """
        Function that get configuration parameters from configfile.ini and
        assigns this params to TorrentBot values
        """
        config = configparser.ConfigParser()
        config.read("configfile.ini")
        if "token" not in config["DEFAULT"]:
            logging.error("There is not Bot token in config file")
            raise Exception("There is not Bot token in config file")
        if "store_path" not in config["DEFAULT"]:
            logging.error("Define path where to store torrent files")
            raise Exception("Path where to store torrent files is not defined")
        self.token = config["DEFAULT"]["token"]
        self.path = config["DEFAULT"]["store_path"]
        if "chat_id" in config["DEFAULT"]:
            self.chat_id = config["DEFAULT"]["chat_id"]
        for user in config["USERNAME"]:
            self.users.add(config["USERNAME"][user])

    def running(self):
        '''
        Function that get update, parse update, download torrent files and
        sends them to torrent client transmission
        '''
        while True:
            result = self.get_update()
            if result:
                # logging.info(result)
                self.offset = result[-1]["update_id"] + 1
                self.parse_update(result)

    def get_update(self):
        '''
        Make GetUpdate request to Telegram Bot API
        Returns array of updates of filed result of the Update object
        Elements of array are dicts
        '''
        endpoint = "https://api.telegram.org/bot{}/getUpdates".format(self.token)
        payload = {"timeout": 60}
        if self.offset:
            payload['offset'] = self.offset
        response = self.make_request(endpoint, payload)
        if response["ok"]:
            return response["result"]
        else:
            # log description if "ok" field of the response is false
            logging.error(response['description'])

    def make_request(self, endpoint, payload=None, method="get"):
        '''
        Make HTTP request
        Input: endpoint, payload and method
        Returnes response in json format
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
            return res.json()
        except Exception:
            logging.exception("error in request_update")

    def parse_update(self, result):
        for update in result:
            user = update["message"]["from"]["username"]
            chat_id = update['message']['chat']['id']
            if user not in self.users:
                self.send_msg("User with username {} is not allowed to send files".format(user), chat_id)
                logging.error("User with username {} is not allowed to send files".format(user))
                return
            if "document" in update["message"]:
                doc_name = update["message"]["document"]["file_name"]
                doc_size = update["message"]["document"]["file_size"]
                if doc_size <= 20*1024*1024 and doc_name.endswith(".torrent"):
                    self.send_msg("you sent torrent file", chat_id)
                    file_id = update["message"]["document"]["file_id"]
                    self.download_file(file_id, new_name(doc_name), chat_id)

    def send_msg(self, message, chat_id):
        '''
        Make sendMessage request to Telegram Bot API
        Sends message to chat with chat_id
        '''
        endpoint = "https://api.telegram.org/bot{}/sendMessage".format(self.token)
        payload = {"chat_id": chat_id, "text": message}
        self.make_request(endpoint, payload, "post")

    def download_file(self, file_id, doc_name, chat_id):
        '''
        '''
        file_obj = self.getFile(file_id)
        if not file_obj:
            return
        file_path = file_obj["file_path"]
        if not file_path:
            return
        endpoint = "https://api.telegram.org/file/bot{}/{}".format(self.token, file_path)
        res = requests.get(url=endpoint)
        # !!! to check response?
        # Check if file doc_name exists
        res_md5hash = count_md5hash_bytes(res.content)
        if res_md5hash in self.md5hash_store.md5hash:
            self.send_msg("This torrent file exists", chat_id)
            return
        self.md5hash_store.add_md5hash(res_md5hash)
        # Rename file if file with name "doc_name" existanse
        doc_name = self.checkFileName(doc_name)
        store_path = "{}/{}".format(self.path, doc_name)
        with open(store_path, "wb") as f:
                f.write(res.content)
                res = None
        self.send_msg("file downloaded", chat_id)

    def getFile(self, file_id):
        '''
        Make getFile request to Telegram Bot API
        Returns value of the result field of File object or None
        '''
        endpoint = "https://api.telegram.org/bot{}/getFile".format(self.token)
        payload = {"file_id": file_id}
        response = self.make_request(endpoint, payload)
        if response["ok"]:
            return response["result"]
        else:
            # log description if "ok" field of the response is false
            logging.error(response['description'])

    def checkFileName(self, doc_name):
        '''
        Check existanse of the file with name "doc_name"
        '''
        checkpath = "{}/{}".format(self.path, doc_name)
        if os.path.isfile(checkpath):
            new_name = doc_name + "_new"
            return new_name
        return doc_name


def new_name(doc_name):
    '''
    Formats the name of the file
    '''
    name_strip = doc_name.strip()
    for old in [" ", "..", "/"]:
        new_name = name_strip.replace(old, "")
    return new_name


def main():
    logging.basicConfig(filename='torrent_bot.log', level=logging.DEBUG)
    luckyBot = TorrentBot()
    luckyBot.running()
