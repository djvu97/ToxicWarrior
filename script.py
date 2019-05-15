import json
import requests
import time
import urllib
from pymongo import MongoClient
import threading

TOKEN = "891003963:AAEUyu-J8TQd9_teAB0pQduNnf7Qb5gl-3A"
URL = "https://api.telegram.org/bot{0}/".format(TOKEN)
myclient = MongoClient(
    "mongodb+srv://hiranyeyg:toxicwarrior@cluster0-ygs1g.mongodb.net/test?retryWrites=true")
mydb = myclient["Toxic"]
mycollections = mydb["allcomments"]


def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    js = get_json_from_url(url)
    return js


def deleteMessage(chatId, messageId, repliedMessageId):
    time.sleep(10)
    url = URL + \
        "deleteMessage?chat_id={}&message_id={}".format(chatId, messageId)
    get_url(url)
    if(repliedMessageId is not None):
        url = URL + \
            "deleteMessage?chat_id={}&message_id={}".format(
                chatId, repliedMessageId)
        get_url(url)


def KickThatPerson(user_id, chat_id, username, groupname):
    url = URL + "sendMessage?text={}&chat_id={}".format(
        "Kicking "+username+" for violation of abuse rule", chat_id)
    get_url(url)
    url = URL+"kickChatMember?chat_id={0}&user_id={1}".format(chat_id, user_id)
    get_url(url)
    url = URL + "sendMessage?text={}&chat_id={}".format(
        "You were kicked by me from Group "+groupname, user_id)
    get_url(url)


def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def echo_all(updates):
    for update in updates["result"]:
        try:
            text = update["message"]["text"]
            if('#toxic' in text):
                repliedMessageId = update["message"]["message_id"]
                comment = update["message"]["reply_to_message"]["text"]
                chat = update["message"]["chat"]["id"]
                groupname = update["message"]["chat"]["title"]
                userid = update["message"]["reply_to_message"]["from"]["id"]
                username = update["message"]["reply_to_message"]["from"]["username"]
                analysisMessage = update["message"]["reply_to_message"]["message_id"]
                send_toxicityReport(comment, userid, chat,
                                    analysisMessage, username, groupname, repliedMessageId)
        except Exception as e:
            print(e)


def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)


def send_toxicityReport(text, user_id, chat_id, analysisMessage, username, groupname, repliedMessageId):

    global tokenizer
    global model
    classes = ["toxic", "severe_toxic", "obscene",
               "threat", "insult", "identity_hate"]
    url = 'https://toxicity-warrior-api.herokuapp.com/analyze'
    params = {'comment': text}
    response = requests.post(url, params)
    pred = []
    for i in response.json():
        pred.append(response.json()[i])
    pred = pred[1:]
    predictedClasses = []
    count = 0
    for i, c in enumerate(classes):
        if(pred[i] > 0.7):
            count += 1
            predictedClasses.append(c)
    s = "This is "
    if len(predictedClasses) >= 1:
        s += predictedClasses[0]
        for i in predictedClasses[1:]:

            if i == predictedClasses[-1]:
                s += " and {}".format(i)
            else:
                s += ", {}".format(i)
    else:
        s += "not abusive."

    text = urllib.parse.quote_plus(s)
    if(count > 0):
        History = mycollections.find_one_and_delete(
            {"userId": user_id, "chatId": chat_id})
        if(History is None):
            History = dict()
            History["userId"] = user_id
            History["chatId"] = chat_id
        try:
            if(analysisMessage not in History["messageID"]):
                History["comment"].append(text)
                History["messageID"].append(analysisMessage)
        except:
            History["comment"] = [text]
            History["messageID"] = [analysisMessage]
        if(len(History["comment"]) > 2):
            KickThatPerson(user_id, chat_id, username, groupname)
        else:
            mycollections.insert_one(History)
            url = URL + "sendMessage?text={}&chat_id={}&reply_to_message_id={}".format(
                "@"+username+",\nI detected this as an abusive message\nThis is your warning no:"+str(len(History["comment"])), chat_id, analysisMessage)
            DeleteThisReportMessage = get_json_from_url(
                url)["result"]["message_id"]
            thread1 = threading.Thread(target=deleteMessage, args=(
                chat_id, DeleteThisReportMessage, None))
            thread1.start()
        thread = threading.Thread(
            target=deleteMessage, args=(chat_id, analysisMessage, repliedMessageId))
        thread.start()
    if(count == 0):
        url = URL + "sendMessage?text={}&chat_id={}&reply_to_message_id={}".format(
            text, chat_id, analysisMessage)
        get_url(url)


def main():
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            echo_all(updates)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
