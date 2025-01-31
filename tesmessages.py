from pymongo import MongoClient
from twitch_chat_irc import twitch_chat_irc
import requests
import certifi
import json
import re
import datetime
import time
from bs4 import BeautifulSoup
import random
import hashlib
import asyncio
import imaplib
import codecs
from config import mongo
from typing import Annotated,Union
from fastapi import Depends, FastAPI, HTTPException, Security, status,Cookie,File,UploadFile,BackgroundTasks
from fastapi import FastAPI,Form, Request,Response,WebSocket
from typing import Optional,List,Dict
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,PlainTextResponse,JSONResponse,RedirectResponse,FileResponse
import uvicorn
import time
import irc.client
from multiprocessing import Manager
from fastapi.middleware.cors import CORSMiddleware
import aiohttp
import asyncio
from async_irc_client.async_irc_client import TwitchIRCBot, Message,Proxy, ProxyType



class MyBot(TwitchIRCBot):

    # subscribe to twitch's irc events
    

    # create commands
    pass

    # repeat a task
    # runs once the client is ready and after the specified time interval
    # here 1000s
    


cluster=MongoClient(mongo)
db=cluster["UsersData"]
collection=db["forms"]
illegals_collection=db["ILLEGALS"]
loggs=db["logs"]
rakbots=db["RAKBOT"]
rakbots_dostup=db["RAKBOT_DOSTUP"]
antiblat_collection=db["ANTIBLAT_21"]
quests_collection=db["QUESTS_21"]
slet_logs=db["SLET_LOGS_21"]
forms_so=db["FORMS_SO"]
forms_po=db["FORMS_PO"]
SITE_USERS=db["SITE_USERS"]
ports=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["ports"]
channel=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
SECRET_KEY="dfafeasfeasfeasfeasfeasfeas"
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://szhnserv.ru"],  # Можно указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],  # Можно указать конкретные HTTP-методы
    allow_headers=["*"],  # Можно указать конкретные заголовки
)
#login_manager = LoginManager(SECRET_KEY,"/auth","/api/testpoisk")


# Остановка планировщика при завершении приложения


start_check=time.time()
connections={}


users_connection={}
list_connection={}
channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
users_list_accept=["charlietheawesome","berdoff","walkonte","shawdfxc","lru_rose"]
for i in users_list_accept:
    connections[i]=[]
    users_connection[i]=[]
    list_connection[i]=[]
print(connections)
users=db["TWITCH_TACHKA"].find_one({"type":"accs"})["tokens"]

@app.get("/",response_class=HTMLResponse)
async def index():
        return "da"



toks={"yahochupivo3214123ferrcefw3cf431fc43": "sekasemaii"}


     



@app.post("/api/twitch/check_connect", response_class=JSONResponse)
async def checkConnect(token: str = Form()):
    global start_check
    global channels
    print(channels, token)

    if token and len(token) < 100 and token in channels:
        channel = channels[token]
        global connections
        global users_connection
        global list_connection

        if time.time() - start_check > 1200:
            # Очистка старых подключений, если прошло больше 20 минут
            connections[channel] = connections[channel][:30]
            start_check = time.time()

        if len(connections[channel]) < 20:
            if channel not in connections:
                connections[channel] = []
            if channel not in users_connection:
                users_connection[channel] = []
            if channel not in list_connection:
                list_connection[channel] = []

            users = db["TWITCH_TACHKA"].find_one({"type": "accs"})["tokens"]
            proxi = db["TWITCH_TACHKA"].find_one({"type": "proxy"})["current_proxy"][token]
            proxi_url = proxi.split("@")[1].split(":")[0]
            proxi_port = int(proxi.split("@")[1].split(":")[1])
            proxi_user = proxi.split(":")[0]
            proxi_pass = proxi.split("@")[0].split(":")[1]
            prox_con = Proxy(ProxyType.HTTP, proxi_url, proxi_port, password=proxi_pass, username=proxi_user)

            vips = db["TWITCH_TACHKA"].find_one({"channel": channel})["vips"]
            for userr in vips:
                if userr not in users_connection[channel]:
                    users_connection[channel].append(userr)
                    list_connection[channel].append({"nick": userr.split(":")[0], "vip": True})
                    token = userr.split(":")[-1]
                    nick = userr.split(":")[0]

                    try:
                        new_bot = MyBot(
                            oauth_token=token, nick_name=nick, channel=channel, proxies=[prox_con]
                        )
                        connections[channel].append({"nick": nick, "token": userr, "bot": new_bot})
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, new_bot.run)
                        print(f"+{nick} acc: {channel}")
                        await asyncio.sleep(1)
                    except Exception as e:
                        print("Except:", e)

            for _ in range(10):
                for _ in range(10):
                    user = random.choice(users)
                    while user in users_connection[channel]:
                        user = random.choice(users)

                    users_connection[channel].append(user)
                    list_connection[channel].append({"nick": user.split(":")[0], "vip": False})

                    token = user.split(":")[-1]
                    nick = user.split(":")[0]

                    try:
                        new_bot = MyBot(
                            oauth_token=token, nick_name=nick, channel=channel, proxies=[prox_con]
                        )
                        connections[channel].append({"nick": nick, "token": user, "bot": new_bot})
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, new_bot.run)
                        print(f"+{nick} acc: {channel}")
                        await asyncio.sleep(1)
                    except Exception as e:
                        print("Except1:", e)
                await asyncio.sleep(4)

        return list_connection[channel]

        

@app.post("/api/twitch/count_connections",response_class=HTMLResponse)
async def checkConnect(token:str=Form()):
    global channels
    if token and len(token)<100 and token in channels:
        channel=channels[token]
        global connections
        if channel in connections:
            pass
        else:
            connections[channel]=[]
        return str(len(connections[channel]))




@app.post("/api/twitch/connect",response_class=HTMLResponse)
async def connectAccs(token:str=Form(),count:str=Form()):
    global channels
    if token and len(token)<100 and token in channels:
        channel=channels[token]
        global connections
        
        global start_check
        global users_connection
        global list_connection
        if count!="all exit":
            
            if not channel in connections:
                
                connections[channel]=[]
                users_connection[channel]=[]
            
            users=db["TWITCH_TACHKA"].find_one({"type":"accs"})["tokens"]
            proxii=db["TWITCH_TACHKA"].find_one({"type":"proxy"})["proxies"]
            print(proxii)
            start_check=time.time()
            for i in range(int(count)):
                user=random.choice(users)
                while user in users_connection[channel]:
                    user=random.choice(users)
                users_connection[channel].append(user)
                proxi=random.choice(proxii)
                proxi_url=proxi.split("@")[1].split(":")[0]
                proxi_port=int(proxi.split("@")[1].split(":")[1])
                proxi_user=proxi.split(":")[0]
                proxi_pass=proxi.split("@")[0].split(":")[1]
                #proxy_url = f'http://{proxi}'
                proxy_url=f"http://{proxi_url}:{proxi_port}"
                #target_url = 'irc://irc.chat.twitch.tv:6667'
                #proxy_auth = aiohttp.BasicAuth(proxi_user, proxi_pass)
                print(proxy_url)
                token=user.split(":")[-1]
                nick=user.split(":")[0]
                try:
                    new_bot=MyBot(oauth_token=token, nick_name=nick, channel=channel,proxies=[Proxy(ProxyType.HTTP, proxi_url, proxi_port, password=proxi_pass, username=proxi_user)])
                    connections[channel].append(new_bot)
                    new_bot.run()
                    print(f"+{i} acc:{channel}")
                except Exception as e: print("Except:",e)
            print(str(len(connections[channel])))
            return str(len(connections[channel]))
                    
        if count=="all exit":
            if channel in connections:
                for i in connections[channel]:
                    i["bot"].leave(channel)
                    await asyncio.sleep(0.2)
                    i["bot"].stop()
                    await asyncio.sleep(0.2)
                        
 
            
            connections[channel]=[]
            users_connection[channel]=[]
            list_connection[channel]=[]
            
            return str(len(connections[channel]))


@app.get("/api/get_proxy",response_class=HTMLResponse)
async def get_proxy(token:str):
    global channels
    if token and len(token)<100 and token in channels:
        return "<br>".join(db["PROXY"].find_one({"type":"proxy"})["list"])


     






@app.post("/twitch/tachka",response_class=HTMLResponse)
async def go_tachka_msg(request: Request,token:str=Form(),msg:str=Form(),nickacc:str = Form(None),use_acc:str = Form(None)):
    global channels
    global connections
    if token and len(token)<300 and token in channels:
        channel=channels[token]
        print(nickacc)
        irc_socket=None
        
        if not nickacc and not use_acc:
            irc_socket=random.choice(connections[channel])
        else:
            print(connections[channel])
            for i in connections[channel]:
                print(i["nick"],nickacc)
                if i["nick"]==nickacc:
                    irc_socket=i
                    break
            if not irc_socket:
                irc_socket=random.choice(connections[channel])
            print("Ник найден")
        if ".txt" in msg:
            a=db["TWITCH_TACHKA"].find_one({"channel":channel})["files"]
            if msg in a:
                msg=random.choice(a[msg].split("\n"))
            print("Соединение активно")
        try:
            conn=irc_socket["bot"]._is_connected
            while not conn:
                try:
                    connections[channel].remove(irc_socket)
                except: pass
                try:
                    users_connection[channel].remove(irc_socket["token"])
                except:
                    pass
                try:
                    list_connection[channel].remove(irc_socket["nick"])
                except:
                    pass
                irc_socket=random.choice(connections[channel])
                conn=irc_socket["bot"]._is_connected
            irc_socket["bot"].send_chat_message(msg)
            print("send",msg,"to",channel)  
        except Exception as e: print("Ошибка отправки",e)
