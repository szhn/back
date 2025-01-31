import requests
from pymongo import MongoClient
from config import mongo
import certifi
import time
cluster=MongoClient(mongo,tlsCAFile=certifi.where())
db=cluster["UsersData"]

urls=[]


ports=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["ports"]
for i in ports:
    port=ports[i]
    print(port,i)
    print(requests.post(f"https://szhnserv.ru:{port}/api/twitch/check_connect",data={"token":i}).text)




