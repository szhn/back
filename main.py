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
import aiohttp
import asyncio
import imaplib
import codecs
from config import mongo
from typing import Annotated,Union
from fastapi import Depends, FastAPI, HTTPException, Security, status,Cookie,File,UploadFile,BackgroundTasks
from fastapi import FastAPI,Form, Request,Response,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional,List,Dict
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,PlainTextResponse,JSONResponse,RedirectResponse,FileResponse
import uvicorn
import irc.client
import threading
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fake_useragent import UserAgent

ua = UserAgent()

templates = Jinja2Templates(directory="templates")
cluster=MongoClient(mongo)
db=cluster["UsersData"]
superchat=db["superchat"]

SECRET_KEY="dfafeasfeasfeasfeasfeasfeas"
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory="static"), name="static")
def query_user(login: str):
    #print(superchat.find_one({"login":login}))
    return superchat.find_one({"login":login}, {'_id': False})



connections={}
users_connection={}
class ConnectionManager:
    #initialize list for websockets connections
    def __init__(self):
        self.active_connections: List[WebSocket] = []
 
    #accept and append the connection to the list
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
 
    #remove the connection from list
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
 
    #send personal message to the connection
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
         
    #send message to the list of connections
    async def broadcast(self, message: str, websocket: WebSocket):
        for connection in self.active_connections:
            if(connection == websocket):
                continue
            await connection.send_text(message)
connectionmanager = ConnectionManager()

@app.get("/",response_class=HTMLResponse)
async def index():
        return "da"

    

@app.get("/api/twitch/chat_tokens",response_class=HTMLResponse)
async def checkConnect(token:str):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<150 and token in channels:
        return "<br>".join(db["TWITCH_TACHKA"].find_one({"type":"accs"})["tokens"])





@app.post("/api/twitch/check_connect",response_class=HTMLResponse)
async def checkConnect(token:str=Form(),channel:str=Form()):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<150 and token in channels:
        channel=channels[token]
        global connections
        global users_connection
        if channel in connections:
            for irc_socket in connections[channel]:
                try:
                    data = irc_socket.recv(4096)
                    message = data.decode("UTF-8")
                    if data[0:4] == "PING":
                        irc_socket.send("PONG " + data.split()[1] + "\n")
                except:
                    irc_socket.close()
        return "True"


@app.post("/api/twitch/connect",response_class=HTMLResponse)
async def connectAccs(token:str=Form(),channel:str=Form(),count:str=Form()):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<150 and token in channels:
        channel=channels[token]
        global connections
        global users_connection
        if count!="all exit":
            if not channel in connections:
                connections[channel]=[]
                users_connection[channel]=[]
            users=db["TWITCH_TACHKA"].find_one({"type":"accs"})["tokens"]
            proxi=db["TWITCH_TACHKA"].find_one({"type":"proxy"})["current_proxy"]
            
            for i in range(int(count)):
                user=random.choice(users)
                while user in users_connection[channel]:
                    user=random.choice(users)
                users_connection[channel].append(user)
                
                proxi_url=proxi.split("@")[1].split(":")[0]
                proxi_port=int(proxi.split("@")[1].split(":")[1])
                proxi_user=proxi.split(":")[0]
                proxi_pass=proxi.split("@")[0].split(":")[1]
                
                
                user=user.split(":")[-1]
                try:
                    proxy = socks.socksocket()
                    proxy.settimeout(2)
                #proxy.setproxy(socks.SOCKS5, proxi_url, proxi_port)
                    proxy.set_proxy(socks.SOCKS5, proxi_url, proxi_port, True, proxi_user, proxi_pass)
                    print(1)
                    # Подключаемся к Twitch IRC с прокси
                    irc_socket = proxy
                    #reader, writer = await asyncio.open_connection("irc.twitch.tv", 6667)
                    irc_socket.connect(("irc.twitch.tv", 6667))
                    print(2)
                    # Отправляем данные для подключения
                    irc_socket.send(bytes(f"PASS oauth:{user}\r\n", "UTF-8"))
                    irc_socket.send(bytes(f"NICK user\r\n", "UTF-8"))
                    irc_socket.send(bytes(f"JOIN {channel}\r\n", "UTF-8"))
                    #writer.write(bytes(f"PASS oauth:{user}\r\n", "UTF-8"))
                    #await writer.drain()
                    #writer.write(bytes(f"NICK user\r\n", "UTF-8"))
                    #await writer.drain()
                    #writer.write(bytes(f"JOIN {channel}\r\n", "UTF-8"))
                    #await writer.drain()
                    #connections[channel].append(writer)
                    connections[channel].append(irc_socket)
                    print(f"+{i} acc:{channel}")
                except:
                    print("error acc")
                    
        else:
            if channel in connections:
                for i in connections[channel]:
                    try:
                        i.close()
                        #await i.wait_closed()
                    except:
                        pass
            connections[channel]=[]
            users_connection[channel]=[]
            
        return str(len(connections[channel]))

@app.get("/yess",response_class=HTMLResponse)
async def indexx():
    return str(len(connections))

@app.get("/api/get_proxy",response_class=HTMLResponse)
async def get_proxy(token:str):
    if len(token)<40 and token in token_berdoff:
        return "<br>".join(db["PROXY"].find_one({"type":"proxy"})["list"])
@app.get("/twitch/emotes",response_class=HTMLResponse)
async def emotes(request: Request):
    global_emotions={'4Head': 'https://static-cdn.jtvnw.net/emoticons/v1/354/1.0', '8-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555579/1.0', ':(': 'https://static-cdn.jtvnw.net/emoticons/v1/2/1.0', ':)': 'https://static-cdn.jtvnw.net/emoticons/v1/1/1.0', ':-(': 'https://static-cdn.jtvnw.net/emoticons/v1/555555559/1.0', ':-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555557/1.0', ':-/': 'https://static-cdn.jtvnw.net/emoticons/v1/555555586/1.0', ':-D': 'https://static-cdn.jtvnw.net/emoticons/v1/555555561/1.0', ':-O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555581/1.0', ':-P': 'https://static-cdn.jtvnw.net/emoticons/v1/555555592/1.0', ':-Z': 'https://static-cdn.jtvnw.net/emoticons/v1/555555568/1.0', ':-\\': 'https://static-cdn.jtvnw.net/emoticons/v1/555555588/1.0', ':-o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555583/1.0', ':-p': 'https://static-cdn.jtvnw.net/emoticons/v1/555555594/1.0', ':-z': 'https://static-cdn.jtvnw.net/emoticons/v1/555555566/1.0', ':-|': 'https://static-cdn.jtvnw.net/emoticons/v1/555555564/1.0', ':/': 'https://static-cdn.jtvnw.net/emoticons/v1/10/1.0', ':D': 'https://static-cdn.jtvnw.net/emoticons/v1/3/1.0', ':O': 'https://static-cdn.jtvnw.net/emoticons/v1/8/1.0', ':P': 'https://static-cdn.jtvnw.net/emoticons/v1/12/1.0', ':Z': 'https://static-cdn.jtvnw.net/emoticons/v1/555555567/1.0', ':\\': 'https://static-cdn.jtvnw.net/emoticons/v1/555555587/1.0', ':o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555582/1.0', ':p': 'https://static-cdn.jtvnw.net/emoticons/v1/555555593/1.0', ':z': 'https://static-cdn.jtvnw.net/emoticons/v1/555555565/1.0', ':|': 'https://static-cdn.jtvnw.net/emoticons/v1/5/1.0', ';)': 'https://static-cdn.jtvnw.net/emoticons/v1/11/1.0', ';-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555590/1.0', ';-P': 'https://static-cdn.jtvnw.net/emoticons/v1/555555596/1.0', ';-p': 'https://static-cdn.jtvnw.net/emoticons/v1/555555598/1.0', ';P': 'https://static-cdn.jtvnw.net/emoticons/v1/13/1.0', ';p': 'https://static-cdn.jtvnw.net/emoticons/v1/555555597/1.0', '<3': 'https://static-cdn.jtvnw.net/emoticons/v1/9/1.0', '>(': 'https://static-cdn.jtvnw.net/emoticons/v1/4/1.0', 'ANELE': 'https://static-cdn.jtvnw.net/emoticons/v1/3792/1.0', 'AnotherRecord': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_9eade28238d64e83b0219a9025d4692d/1.0', 'ArgieB8': 'https://static-cdn.jtvnw.net/emoticons/v1/51838/1.0', 'ArsonNoSexy': 'https://static-cdn.jtvnw.net/emoticons/v1/50/1.0', 'AsexualPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827267/1.0', 'AsianGlow': 'https://static-cdn.jtvnw.net/emoticons/v1/74/1.0', 'B)': 'https://static-cdn.jtvnw.net/emoticons/v1/7/1.0', 'B-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555578/1.0', 'BCWarrior': 'https://static-cdn.jtvnw.net/emoticons/v1/30/1.0', 'BOP': 'https://static-cdn.jtvnw.net/emoticons/v1/301428702/1.0', 'BabyRage': 'https://static-cdn.jtvnw.net/emoticons/v1/22639/1.0', 'BangbooBounce': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_f9feac06649548448b3127dd9bd7710e/1.0', 'BatChest': 'https://static-cdn.jtvnw.net/emoticons/v1/115234/1.0', 'BegWan': 'https://static-cdn.jtvnw.net/emoticons/v1/160394/1.0', 'BibleThump': 'https://static-cdn.jtvnw.net/emoticons/v1/86/1.0', 'BigBrother': 'https://static-cdn.jtvnw.net/emoticons/v1/1904/1.0', 'BigPhish': 'https://static-cdn.jtvnw.net/emoticons/v1/160395/1.0', 'BisexualPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827313/1.0', 'BlackLivesMatter': 'https://static-cdn.jtvnw.net/emoticons/v1/302537250/1.0', 'BlargNaut': 'https://static-cdn.jtvnw.net/emoticons/v1/114738/1.0', 'BloodTrail': 'https://static-cdn.jtvnw.net/emoticons/v1/69/1.0', 'BrainSlug': 'https://static-cdn.jtvnw.net/emoticons/v1/115233/1.0', 'BrokeBack': 'https://static-cdn.jtvnw.net/emoticons/v1/4057/1.0', 'BuddhaBar': 'https://static-cdn.jtvnw.net/emoticons/v1/27602/1.0', 'BunnyCharge': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_b5751982f59347b78f51691f2b08d445/1.0', 'CaitlynS': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_4acac638cffb4db49f376059f7077dae/1.0', 'CarlSmile': 'https://static-cdn.jtvnw.net/emoticons/v1/166266/1.0', 'ChefFrank': 'https://static-cdn.jtvnw.net/emoticons/v1/90129/1.0', 'ChewyYAY': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_0e0a3592d8334ef5a1cfcae6f3e76acb/1.0', 'CoolCat': 'https://static-cdn.jtvnw.net/emoticons/v1/58127/1.0', 'CoolStoryBob': 'https://static-cdn.jtvnw.net/emoticons/v1/123171/1.0', 'CorgiDerp': 'https://static-cdn.jtvnw.net/emoticons/v1/49106/1.0', 'CrreamAwk': 'https://static-cdn.jtvnw.net/emoticons/v1/191313/1.0', 'CurseLit': 'https://static-cdn.jtvnw.net/emoticons/v1/116625/1.0', 'DAESuppy': 'https://static-cdn.jtvnw.net/emoticons/v1/973/1.0', 'DBstyle': 'https://static-cdn.jtvnw.net/emoticons/v1/73/1.0', 'DansGame': 'https://static-cdn.jtvnw.net/emoticons/v1/33/1.0', 'DarkKnight': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_d9567e500d78441793bee538dcabc1da/1.0', 'DarkMode': 'https://static-cdn.jtvnw.net/emoticons/v1/461298/1.0', 'DatSheffy': 'https://static-cdn.jtvnw.net/emoticons/v1/111700/1.0', 'DendiFace': 'https://static-cdn.jtvnw.net/emoticons/v1/58135/1.0', 'DinoDance': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_dcd06b30a5c24f6eb871e8f5edbd44f7/1.0', 'DogFace': 'https://static-cdn.jtvnw.net/emoticons/v1/114835/1.0', 'DoritosChip': 'https://static-cdn.jtvnw.net/emoticons/v1/102242/1.0', 'DxCat': 'https://static-cdn.jtvnw.net/emoticons/v1/110734/1.0', 'EarthDay': 'https://static-cdn.jtvnw.net/emoticons/v1/959018/1.0', 'EleGiggle': 'https://static-cdn.jtvnw.net/emoticons/v1/4339/1.0', 'EntropyWins': 'https://static-cdn.jtvnw.net/emoticons/v1/376765/1.0', 'ExtraLife': 'https://static-cdn.jtvnw.net/emoticons/v1/302426269/1.0', 'FBBlock': 'https://static-cdn.jtvnw.net/emoticons/v1/1441276/1.0', 'FBCatch': 'https://static-cdn.jtvnw.net/emoticons/v1/1441281/1.0', 'FBChallenge': 'https://static-cdn.jtvnw.net/emoticons/v1/1441285/1.0', 'FBPass': 'https://static-cdn.jtvnw.net/emoticons/v1/1441271/1.0', 'FBPenalty': 'https://static-cdn.jtvnw.net/emoticons/v1/1441289/1.0', 'FBRun': 'https://static-cdn.jtvnw.net/emoticons/v1/1441261/1.0', 'FBSpiral': 'https://static-cdn.jtvnw.net/emoticons/v1/1441273/1.0', 'FBtouchdown': 'https://static-cdn.jtvnw.net/emoticons/v1/626795/1.0', 'FUNgineer': 'https://static-cdn.jtvnw.net/emoticons/v1/244/1.0', 'FailFish': 'https://static-cdn.jtvnw.net/emoticons/v1/360/1.0', 'FallCry': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_2734f1a85677416a9d8f846a2d1b4721/1.0', 'FallHalp': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_7f9b025d534544afaf679e13fbd47b88/1.0', 'FallWinning': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_dee4ecfb7f0940bead9765da02c57ca9/1.0', 'FamilyMan': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_89f3f0761c7b4f708061e9e4be3b7d17/1.0', 'FlawlessVictory': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_0cb91e8a01c741fe9d4a0607f70395db/1.0', 'FootBall': 'https://static-cdn.jtvnw.net/emoticons/v1/302628600/1.0', 'FootGoal': 'https://static-cdn.jtvnw.net/emoticons/v1/302628617/1.0', 'FootYellow': 'https://static-cdn.jtvnw.net/emoticons/v1/302628613/1.0', 'ForSigmar': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_db3385fb0ea54913bf58fa5554edfdf2/1.0', 'FrankerZ': 'https://static-cdn.jtvnw.net/emoticons/v1/65/1.0', 'FreakinStinkin': 'https://static-cdn.jtvnw.net/emoticons/v1/117701/1.0', 'FutureMan': 'https://static-cdn.jtvnw.net/emoticons/v1/98562/1.0', 'GayPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827321/1.0', 'GenderFluidPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827326/1.0', 'Getcamped': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_291135bb36d24d33bf53860128b5095c/1.0', 'GingerPower': 'https://static-cdn.jtvnw.net/emoticons/v1/32/1.0', 'GivePLZ': 'https://static-cdn.jtvnw.net/emoticons/v1/112291/1.0', 'GlitchCat': 'https://static-cdn.jtvnw.net/emoticons/v1/304486301/1.0', 'GlitchLit': 'https://static-cdn.jtvnw.net/emoticons/v1/304489128/1.0', 'GlitchNRG': 'https://static-cdn.jtvnw.net/emoticons/v1/304489309/1.0', 'GoatEmotey': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_e41e4d6808224f25ae1fb625aa26de63/1.0', 'GoldPLZ': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_c1f4899e65cf4f53b2fd98e15733973a/1.0', 'GrammarKing': 'https://static-cdn.jtvnw.net/emoticons/v1/3632/1.0', 'GunRun': 'https://static-cdn.jtvnw.net/emoticons/v1/1584743/1.0', 'HSCheers': 'https://static-cdn.jtvnw.net/emoticons/v1/444572/1.0', 'HSWP': 'https://static-cdn.jtvnw.net/emoticons/v1/446979/1.0', 'HarleyWink': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_8b0ac3eee4274a75868e3d0686d7b6f7/1.0', 'HassaanChop': 'https://static-cdn.jtvnw.net/emoticons/v1/20225/1.0', 'HeyGuys': 'https://static-cdn.jtvnw.net/emoticons/v1/30259/1.0', 'HolidayCookie': 'https://static-cdn.jtvnw.net/emoticons/v1/1713813/1.0', 'HolidayLog': 'https://static-cdn.jtvnw.net/emoticons/v1/1713816/1.0', 'HolidayPresent': 'https://static-cdn.jtvnw.net/emoticons/v1/1713819/1.0', 'HolidaySanta': 'https://static-cdn.jtvnw.net/emoticons/v1/1713822/1.0', 'HolidayTree': 'https://static-cdn.jtvnw.net/emoticons/v1/1713825/1.0', 'HotPokket': 'https://static-cdn.jtvnw.net/emoticons/v1/357/1.0', 'HungryPaimon': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_535e40afa0b34a9481997627b1b47d96/1.0', 'ImTyping': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_b0c6ccb3b12b4f99a9cc83af365a09f1/1.0', 'IntersexPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827332/1.0', 'InuyoFace': 'https://static-cdn.jtvnw.net/emoticons/v1/160396/1.0', 'ItsBoshyTime': 'https://static-cdn.jtvnw.net/emoticons/v1/133468/1.0', 'JKanStyle': 'https://static-cdn.jtvnw.net/emoticons/v1/15/1.0', 'Jebaited': 'https://static-cdn.jtvnw.net/emoticons/v1/114836/1.0', 'Jebasted': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_031bf329c21040a897d55ef471da3dd3/1.0', 'JonCarnage': 'https://static-cdn.jtvnw.net/emoticons/v1/26/1.0', 'KAPOW': 'https://static-cdn.jtvnw.net/emoticons/v1/133537/1.0', 'KEKHeim': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_7c5d25facc384c47963d25a5057a0b40/1.0', 'Kappa': 'https://static-cdn.jtvnw.net/emoticons/v1/80393/1.0', 'KappaClaus': 'https://static-cdn.jtvnw.net/emoticons/v1/74510/1.0', 'KappaPride': 'https://static-cdn.jtvnw.net/emoticons/v1/55338/1.0', 'KappaRoss': 'https://static-cdn.jtvnw.net/emoticons/v1/70433/1.0', 'KappaWealth': 'https://static-cdn.jtvnw.net/emoticons/v1/81997/1.0', 'Kappu': 'https://static-cdn.jtvnw.net/emoticons/v1/160397/1.0', 'Keepo': 'https://static-cdn.jtvnw.net/emoticons/v1/1902/1.0', 'KevinTurtle': 'https://static-cdn.jtvnw.net/emoticons/v1/40/1.0', 'KingWorldCup': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_533b8c4a9f6e4bfbb528ad39974e3481/1.0', 'Kippa': 'https://static-cdn.jtvnw.net/emoticons/v1/1901/1.0', 'KomodoHype': 'https://static-cdn.jtvnw.net/emoticons/v1/81273/1.0', 'KonCha': 'https://static-cdn.jtvnw.net/emoticons/v1/160400/1.0', 'Kreygasm': 'https://static-cdn.jtvnw.net/emoticons/v1/41/1.0', 'LUL': 'https://static-cdn.jtvnw.net/emoticons/v1/425618/1.0', 'LaundryBasket': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_ecb0bfd49b3c4325864b948d46c8152b/1.0', 'Lechonk': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_665235901db747b1bd395a5f1c0ab8a9/1.0', 'LesbianPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827340/1.0', 'LionOfYara': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_adfadf0ae06a4258adc865761746b227/1.0', 'MVGame': 'https://static-cdn.jtvnw.net/emoticons/v1/142140/1.0', 'Mau5': 'https://static-cdn.jtvnw.net/emoticons/v1/30134/1.0', 'MaxLOL': 'https://static-cdn.jtvnw.net/emoticons/v1/1290325/1.0', 'MechaRobot': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_0be25a1663bd472495b91e0302cec166/1.0', 'MercyWing1': 'https://static-cdn.jtvnw.net/emoticons/v1/1003187/1.0', 'MercyWing2': 'https://static-cdn.jtvnw.net/emoticons/v1/1003189/1.0', 'MikeHogu': 'https://static-cdn.jtvnw.net/emoticons/v1/81636/1.0', 'MingLee': 'https://static-cdn.jtvnw.net/emoticons/v1/68856/1.0', 'ModLove': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_a2dfbbbbf66f4a75b0f53db841523e6c/1.0', 'MorphinTime': 'https://static-cdn.jtvnw.net/emoticons/v1/156787/1.0', 'MrDestructoid': 'https://static-cdn.jtvnw.net/emoticons/v1/28/1.0', 'MyAvatar': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_c0c9c932c82244ff920ad2134be90afb/1.0', 'NewRecord': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_53f6a6af8b0e453d874bbefee49b3e73/1.0', 'NiceTry': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_1f524be9838146e3bc9e529c17f797d3/1.0', 'NinjaGrumpy': 'https://static-cdn.jtvnw.net/emoticons/v1/138325/1.0', 'NomNom': 'https://static-cdn.jtvnw.net/emoticons/v1/90075/1.0', 'NonbinaryPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827356/1.0', 'NotATK': 'https://static-cdn.jtvnw.net/emoticons/v1/34875/1.0', 'NotLikeThis': 'https://static-cdn.jtvnw.net/emoticons/v1/58765/1.0', 'O.O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555572/1.0', 'O.o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555570/1.0', 'OSFrog': 'https://static-cdn.jtvnw.net/emoticons/v1/81248/1.0', 'O_O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555571/1.0', 'O_o': 'https://static-cdn.jtvnw.net/emoticons/v1/6/1.0', 'OhMyDog': 'https://static-cdn.jtvnw.net/emoticons/v1/81103/1.0', 'OneHand': 'https://static-cdn.jtvnw.net/emoticons/v1/66/1.0', 'OpieOP': 'https://static-cdn.jtvnw.net/emoticons/v1/100590/1.0', 'OptimizePrime': 'https://static-cdn.jtvnw.net/emoticons/v1/16/1.0', 'PJSalt': 'https://static-cdn.jtvnw.net/emoticons/v1/36/1.0', 'PJSugar': 'https://static-cdn.jtvnw.net/emoticons/v1/102556/1.0', 'PMSTwin': 'https://static-cdn.jtvnw.net/emoticons/v1/92/1.0', 'PRChase': 'https://static-cdn.jtvnw.net/emoticons/v1/28328/1.0', 'PanicVis': 'https://static-cdn.jtvnw.net/emoticons/v1/3668/1.0', 'PansexualPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827370/1.0', 'PartyHat': 'https://static-cdn.jtvnw.net/emoticons/v1/965738/1.0', 'PartyTime': 'https://static-cdn.jtvnw.net/emoticons/v1/135393/1.0', 'PeoplesChamp': 'https://static-cdn.jtvnw.net/emoticons/v1/3412/1.0', 'PermaSmug': 'https://static-cdn.jtvnw.net/emoticons/v1/27509/1.0', 'PicoMause': 'https://static-cdn.jtvnw.net/emoticons/v1/111300/1.0', 'PikaRamen': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_a25ad7124e584c949e2f63917e3d747a/1.0', 'PinkMercy': 'https://static-cdn.jtvnw.net/emoticons/v1/1003190/1.0', 'PipeHype': 'https://static-cdn.jtvnw.net/emoticons/v1/4240/1.0', 'PixelBob': 'https://static-cdn.jtvnw.net/emoticons/v1/1547903/1.0', 'PizzaTime': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_f202746ed88f4e7c872b50b1f7fd78cc/1.0', 'PogBones': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_30050f4353aa4322b25b6b044703e5d1/1.0', 'PogChamp': 'https://static-cdn.jtvnw.net/emoticons/v1/305954156/1.0', 'Poooound': 'https://static-cdn.jtvnw.net/emoticons/v1/117484/1.0', 'PopCorn': 'https://static-cdn.jtvnw.net/emoticons/v1/724216/1.0', 'PopGhost': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_cff32f43571543828847738e27acf4ef/1.0', 'PopNemo': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_5d523adb8bbb4786821cd7091e47da21/1.0', 'PoroSad': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_4c39207000564711868f3196cc0a8748/1.0', 'PotFriend': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_e02650251d204198923de93a0c62f5f5/1.0', 'PowerUpL': 'https://static-cdn.jtvnw.net/emoticons/v1/425688/1.0', 'PowerUpR': 'https://static-cdn.jtvnw.net/emoticons/v1/425671/1.0', 'PraiseIt': 'https://static-cdn.jtvnw.net/emoticons/v1/38586/1.0', 'PrimeMe': 'https://static-cdn.jtvnw.net/emoticons/v1/115075/1.0', 'PunOko': 'https://static-cdn.jtvnw.net/emoticons/v1/160401/1.0', 'PunchTrees': 'https://static-cdn.jtvnw.net/emoticons/v1/47/1.0', 'R)': 'https://static-cdn.jtvnw.net/emoticons/v1/14/1.0', 'R-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555600/1.0', 'RaccAttack': 'https://static-cdn.jtvnw.net/emoticons/v1/114870/1.0', 'RalpherZ': 'https://static-cdn.jtvnw.net/emoticons/v1/1900/1.0', 'RedCoat': 'https://static-cdn.jtvnw.net/emoticons/v1/22/1.0', 'ResidentSleeper': 'https://static-cdn.jtvnw.net/emoticons/v1/245/1.0', 'RitzMitz': 'https://static-cdn.jtvnw.net/emoticons/v1/4338/1.0', 'RlyTho': 'https://static-cdn.jtvnw.net/emoticons/v1/134256/1.0', 'RuleFive': 'https://static-cdn.jtvnw.net/emoticons/v1/107030/1.0', 'RyuChamp': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_0ebc590ba68447269831af61d8bc9e0d/1.0', 'SMOrc': 'https://static-cdn.jtvnw.net/emoticons/v1/52/1.0', 'SSSsss': 'https://static-cdn.jtvnw.net/emoticons/v1/46/1.0', 'SUBprise': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_fcbeed664f7c47d6ba3b57691275ef51/1.0', 'SabaPing': 'https://static-cdn.jtvnw.net/emoticons/v1/160402/1.0', 'SeemsGood': 'https://static-cdn.jtvnw.net/emoticons/v1/64138/1.0', 'SeriousSloth': 'https://static-cdn.jtvnw.net/emoticons/v1/81249/1.0', 'ShadyLulu': 'https://static-cdn.jtvnw.net/emoticons/v1/52492/1.0', 'ShazBotstix': 'https://static-cdn.jtvnw.net/emoticons/v1/87/1.0', 'Shush': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_819621bcb8f44566a1bd8ea63d06c58f/1.0', 'SingsMic': 'https://static-cdn.jtvnw.net/emoticons/v1/300116349/1.0', 'SingsNote': 'https://static-cdn.jtvnw.net/emoticons/v1/300116350/1.0', 'SmoocherZ': 'https://static-cdn.jtvnw.net/emoticons/v1/89945/1.0', 'SoBayed': 'https://static-cdn.jtvnw.net/emoticons/v1/1906/1.0', 'SoonerLater': 'https://static-cdn.jtvnw.net/emoticons/v1/2113050/1.0', 'Squid1': 'https://static-cdn.jtvnw.net/emoticons/v1/191762/1.0', 'Squid2': 'https://static-cdn.jtvnw.net/emoticons/v1/191763/1.0', 'Squid3': 'https://static-cdn.jtvnw.net/emoticons/v1/191764/1.0', 'Squid4': 'https://static-cdn.jtvnw.net/emoticons/v1/191767/1.0', 'StinkyCheese': 'https://static-cdn.jtvnw.net/emoticons/v1/90076/1.0', 'StinkyGlitch': 'https://static-cdn.jtvnw.net/emoticons/v1/304486324/1.0', 'StoneLightning': 'https://static-cdn.jtvnw.net/emoticons/v1/17/1.0', 'StrawBeary': 'https://static-cdn.jtvnw.net/emoticons/v1/114876/1.0', 'SuperVinlin': 'https://static-cdn.jtvnw.net/emoticons/v1/118772/1.0', 'SwiftRage': 'https://static-cdn.jtvnw.net/emoticons/v1/34/1.0', 'TBAngel': 'https://static-cdn.jtvnw.net/emoticons/v1/143490/1.0', 'TF2John': 'https://static-cdn.jtvnw.net/emoticons/v1/1899/1.0', 'TPFufun': 'https://static-cdn.jtvnw.net/emoticons/v1/508650/1.0', 'TPcrunchyroll': 'https://static-cdn.jtvnw.net/emoticons/v1/323914/1.0', 'TTours': 'https://static-cdn.jtvnw.net/emoticons/v1/38436/1.0', 'TakeNRG': 'https://static-cdn.jtvnw.net/emoticons/v1/112292/1.0', 'TearGlove': 'https://static-cdn.jtvnw.net/emoticons/v1/160403/1.0', 'TehePelo': 'https://static-cdn.jtvnw.net/emoticons/v1/160404/1.0', 'ThankEgg': 'https://static-cdn.jtvnw.net/emoticons/v1/160392/1.0', 'TheIlluminati': 'https://static-cdn.jtvnw.net/emoticons/v1/145315/1.0', 'TheRinger': 'https://static-cdn.jtvnw.net/emoticons/v1/18/1.0', 'TheTarFu': 'https://static-cdn.jtvnw.net/emoticons/v1/111351/1.0', 'TheThing': 'https://static-cdn.jtvnw.net/emoticons/v1/7427/1.0', 'ThunBeast': 'https://static-cdn.jtvnw.net/emoticons/v1/1898/1.0', 'TinyFace': 'https://static-cdn.jtvnw.net/emoticons/v1/111119/1.0', 'TombRaid': 'https://static-cdn.jtvnw.net/emoticons/v1/864205/1.0', 'TooSpicy': 'https://static-cdn.jtvnw.net/emoticons/v1/114846/1.0', 'TransgenderPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827377/1.0', 'TriHard': 'https://static-cdn.jtvnw.net/emoticons/v1/120232/1.0', 'TwitchConHYPE': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_13b6dd7f3a3146ef8dc10f66d8b42a96/1.0', 'TwitchLit': 'https://static-cdn.jtvnw.net/emoticons/v1/166263/1.0', 'TwitchRPG': 'https://static-cdn.jtvnw.net/emoticons/v1/1220086/1.0', 'TwitchSings': 'https://static-cdn.jtvnw.net/emoticons/v1/300116344/1.0', 'TwitchUnity': 'https://static-cdn.jtvnw.net/emoticons/v1/196892/1.0', 'TwitchVotes': 'https://static-cdn.jtvnw.net/emoticons/v1/479745/1.0', 'UWot': 'https://static-cdn.jtvnw.net/emoticons/v1/134255/1.0', 'UnSane': 'https://static-cdn.jtvnw.net/emoticons/v1/111792/1.0', 'UncleNox': 'https://static-cdn.jtvnw.net/emoticons/v1/114856/1.0', 'VirtualHug': 'https://static-cdn.jtvnw.net/emoticons/v1/301696583/1.0', 'VoHiYo': 'https://static-cdn.jtvnw.net/emoticons/v1/81274/1.0', 'VoteNay': 'https://static-cdn.jtvnw.net/emoticons/v1/106294/1.0', 'VoteYea': 'https://static-cdn.jtvnw.net/emoticons/v1/106293/1.0', 'WTRuck': 'https://static-cdn.jtvnw.net/emoticons/v1/114847/1.0', 'WholeWheat': 'https://static-cdn.jtvnw.net/emoticons/v1/1896/1.0', 'WhySoSerious': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_1fda4a1b40094c93af334f8b60868a7c/1.0', 'WutFace': 'https://static-cdn.jtvnw.net/emoticons/v1/28087/1.0', 'YouDontSay': 'https://static-cdn.jtvnw.net/emoticons/v1/134254/1.0', 'YouWHY': 'https://static-cdn.jtvnw.net/emoticons/v1/4337/1.0', 'bleedPurple': 'https://static-cdn.jtvnw.net/emoticons/v1/62835/1.0', 'cmonBruh': 'https://static-cdn.jtvnw.net/emoticons/v1/84608/1.0', 'copyThis': 'https://static-cdn.jtvnw.net/emoticons/v1/112288/1.0', 'duDudu': 'https://static-cdn.jtvnw.net/emoticons/v1/62834/1.0', 'imGlitch': 'https://static-cdn.jtvnw.net/emoticons/v1/112290/1.0', 'mcaT': 'https://static-cdn.jtvnw.net/emoticons/v1/35063/1.0', 'o.O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555574/1.0', 'o.o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555576/1.0', 'o_O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555573/1.0', 'o_o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555575/1.0', 'panicBasket': 'https://static-cdn.jtvnw.net/emoticons/v1/22998/1.0', 'pastaThat': 'https://static-cdn.jtvnw.net/emoticons/v1/112289/1.0', 'riPepperonis': 'https://static-cdn.jtvnw.net/emoticons/v1/62833/1.0', 'twitchRaid': 'https://static-cdn.jtvnw.net/emoticons/v1/62836/1.0'}


    return templates.TemplateResponse("emotes.html",{"request":request,"emotes":global_emotions})

@app.get("/twitch/tachka",response_class=HTMLResponse)
async def get_tachka(request: Request,token:Optional[str] = None,auth:Optional[str] = None,style:Optional[str] = None):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<80 and token in channels:
        channel=channels[token]
        global connections
        global_emotions={'4Head': 'https://static-cdn.jtvnw.net/emoticons/v1/354/1.0', '8-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555579/1.0', ':(': 'https://static-cdn.jtvnw.net/emoticons/v1/2/1.0', ':)': 'https://static-cdn.jtvnw.net/emoticons/v1/1/1.0', ':-(': 'https://static-cdn.jtvnw.net/emoticons/v1/555555559/1.0', ':-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555557/1.0', ':-/': 'https://static-cdn.jtvnw.net/emoticons/v1/555555586/1.0', ':-D': 'https://static-cdn.jtvnw.net/emoticons/v1/555555561/1.0', ':-O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555581/1.0', ':-P': 'https://static-cdn.jtvnw.net/emoticons/v1/555555592/1.0', ':-Z': 'https://static-cdn.jtvnw.net/emoticons/v1/555555568/1.0', ':-\\': 'https://static-cdn.jtvnw.net/emoticons/v1/555555588/1.0', ':-o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555583/1.0', ':-p': 'https://static-cdn.jtvnw.net/emoticons/v1/555555594/1.0', ':-z': 'https://static-cdn.jtvnw.net/emoticons/v1/555555566/1.0', ':-|': 'https://static-cdn.jtvnw.net/emoticons/v1/555555564/1.0', ':/': 'https://static-cdn.jtvnw.net/emoticons/v1/10/1.0', ':D': 'https://static-cdn.jtvnw.net/emoticons/v1/3/1.0', ':O': 'https://static-cdn.jtvnw.net/emoticons/v1/8/1.0', ':P': 'https://static-cdn.jtvnw.net/emoticons/v1/12/1.0', ':Z': 'https://static-cdn.jtvnw.net/emoticons/v1/555555567/1.0', ':\\': 'https://static-cdn.jtvnw.net/emoticons/v1/555555587/1.0', ':o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555582/1.0', ':p': 'https://static-cdn.jtvnw.net/emoticons/v1/555555593/1.0', ':z': 'https://static-cdn.jtvnw.net/emoticons/v1/555555565/1.0', ':|': 'https://static-cdn.jtvnw.net/emoticons/v1/5/1.0', ';)': 'https://static-cdn.jtvnw.net/emoticons/v1/11/1.0', ';-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555590/1.0', ';-P': 'https://static-cdn.jtvnw.net/emoticons/v1/555555596/1.0', ';-p': 'https://static-cdn.jtvnw.net/emoticons/v1/555555598/1.0', ';P': 'https://static-cdn.jtvnw.net/emoticons/v1/13/1.0', ';p': 'https://static-cdn.jtvnw.net/emoticons/v1/555555597/1.0', '<3': 'https://static-cdn.jtvnw.net/emoticons/v1/9/1.0', '>(': 'https://static-cdn.jtvnw.net/emoticons/v1/4/1.0', 'ANELE': 'https://static-cdn.jtvnw.net/emoticons/v1/3792/1.0', 'AnotherRecord': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_9eade28238d64e83b0219a9025d4692d/1.0', 'ArgieB8': 'https://static-cdn.jtvnw.net/emoticons/v1/51838/1.0', 'ArsonNoSexy': 'https://static-cdn.jtvnw.net/emoticons/v1/50/1.0', 'AsexualPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827267/1.0', 'AsianGlow': 'https://static-cdn.jtvnw.net/emoticons/v1/74/1.0', 'B)': 'https://static-cdn.jtvnw.net/emoticons/v1/7/1.0', 'B-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555578/1.0', 'BCWarrior': 'https://static-cdn.jtvnw.net/emoticons/v1/30/1.0', 'BOP': 'https://static-cdn.jtvnw.net/emoticons/v1/301428702/1.0', 'BabyRage': 'https://static-cdn.jtvnw.net/emoticons/v1/22639/1.0', 'BangbooBounce': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_f9feac06649548448b3127dd9bd7710e/1.0', 'BatChest': 'https://static-cdn.jtvnw.net/emoticons/v1/115234/1.0', 'BegWan': 'https://static-cdn.jtvnw.net/emoticons/v1/160394/1.0', 'BibleThump': 'https://static-cdn.jtvnw.net/emoticons/v1/86/1.0', 'BigBrother': 'https://static-cdn.jtvnw.net/emoticons/v1/1904/1.0', 'BigPhish': 'https://static-cdn.jtvnw.net/emoticons/v1/160395/1.0', 'BisexualPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827313/1.0', 'BlackLivesMatter': 'https://static-cdn.jtvnw.net/emoticons/v1/302537250/1.0', 'BlargNaut': 'https://static-cdn.jtvnw.net/emoticons/v1/114738/1.0', 'BloodTrail': 'https://static-cdn.jtvnw.net/emoticons/v1/69/1.0', 'BrainSlug': 'https://static-cdn.jtvnw.net/emoticons/v1/115233/1.0', 'BrokeBack': 'https://static-cdn.jtvnw.net/emoticons/v1/4057/1.0', 'BuddhaBar': 'https://static-cdn.jtvnw.net/emoticons/v1/27602/1.0', 'BunnyCharge': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_b5751982f59347b78f51691f2b08d445/1.0', 'CaitlynS': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_4acac638cffb4db49f376059f7077dae/1.0', 'CarlSmile': 'https://static-cdn.jtvnw.net/emoticons/v1/166266/1.0', 'ChefFrank': 'https://static-cdn.jtvnw.net/emoticons/v1/90129/1.0', 'ChewyYAY': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_0e0a3592d8334ef5a1cfcae6f3e76acb/1.0', 'CoolCat': 'https://static-cdn.jtvnw.net/emoticons/v1/58127/1.0', 'CoolStoryBob': 'https://static-cdn.jtvnw.net/emoticons/v1/123171/1.0', 'CorgiDerp': 'https://static-cdn.jtvnw.net/emoticons/v1/49106/1.0', 'CrreamAwk': 'https://static-cdn.jtvnw.net/emoticons/v1/191313/1.0', 'CurseLit': 'https://static-cdn.jtvnw.net/emoticons/v1/116625/1.0', 'DAESuppy': 'https://static-cdn.jtvnw.net/emoticons/v1/973/1.0', 'DBstyle': 'https://static-cdn.jtvnw.net/emoticons/v1/73/1.0', 'DansGame': 'https://static-cdn.jtvnw.net/emoticons/v1/33/1.0', 'DarkKnight': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_d9567e500d78441793bee538dcabc1da/1.0', 'DarkMode': 'https://static-cdn.jtvnw.net/emoticons/v1/461298/1.0', 'DatSheffy': 'https://static-cdn.jtvnw.net/emoticons/v1/111700/1.0', 'DendiFace': 'https://static-cdn.jtvnw.net/emoticons/v1/58135/1.0', 'DinoDance': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_dcd06b30a5c24f6eb871e8f5edbd44f7/1.0', 'DogFace': 'https://static-cdn.jtvnw.net/emoticons/v1/114835/1.0', 'DoritosChip': 'https://static-cdn.jtvnw.net/emoticons/v1/102242/1.0', 'DxCat': 'https://static-cdn.jtvnw.net/emoticons/v1/110734/1.0', 'EarthDay': 'https://static-cdn.jtvnw.net/emoticons/v1/959018/1.0', 'EleGiggle': 'https://static-cdn.jtvnw.net/emoticons/v1/4339/1.0', 'EntropyWins': 'https://static-cdn.jtvnw.net/emoticons/v1/376765/1.0', 'ExtraLife': 'https://static-cdn.jtvnw.net/emoticons/v1/302426269/1.0', 'FBBlock': 'https://static-cdn.jtvnw.net/emoticons/v1/1441276/1.0', 'FBCatch': 'https://static-cdn.jtvnw.net/emoticons/v1/1441281/1.0', 'FBChallenge': 'https://static-cdn.jtvnw.net/emoticons/v1/1441285/1.0', 'FBPass': 'https://static-cdn.jtvnw.net/emoticons/v1/1441271/1.0', 'FBPenalty': 'https://static-cdn.jtvnw.net/emoticons/v1/1441289/1.0', 'FBRun': 'https://static-cdn.jtvnw.net/emoticons/v1/1441261/1.0', 'FBSpiral': 'https://static-cdn.jtvnw.net/emoticons/v1/1441273/1.0', 'FBtouchdown': 'https://static-cdn.jtvnw.net/emoticons/v1/626795/1.0', 'FUNgineer': 'https://static-cdn.jtvnw.net/emoticons/v1/244/1.0', 'FailFish': 'https://static-cdn.jtvnw.net/emoticons/v1/360/1.0', 'FallCry': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_2734f1a85677416a9d8f846a2d1b4721/1.0', 'FallHalp': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_7f9b025d534544afaf679e13fbd47b88/1.0', 'FallWinning': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_dee4ecfb7f0940bead9765da02c57ca9/1.0', 'FamilyMan': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_89f3f0761c7b4f708061e9e4be3b7d17/1.0', 'FlawlessVictory': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_0cb91e8a01c741fe9d4a0607f70395db/1.0', 'FootBall': 'https://static-cdn.jtvnw.net/emoticons/v1/302628600/1.0', 'FootGoal': 'https://static-cdn.jtvnw.net/emoticons/v1/302628617/1.0', 'FootYellow': 'https://static-cdn.jtvnw.net/emoticons/v1/302628613/1.0', 'ForSigmar': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_db3385fb0ea54913bf58fa5554edfdf2/1.0', 'FrankerZ': 'https://static-cdn.jtvnw.net/emoticons/v1/65/1.0', 'FreakinStinkin': 'https://static-cdn.jtvnw.net/emoticons/v1/117701/1.0', 'FutureMan': 'https://static-cdn.jtvnw.net/emoticons/v1/98562/1.0', 'GayPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827321/1.0', 'GenderFluidPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827326/1.0', 'Getcamped': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_291135bb36d24d33bf53860128b5095c/1.0', 'GingerPower': 'https://static-cdn.jtvnw.net/emoticons/v1/32/1.0', 'GivePLZ': 'https://static-cdn.jtvnw.net/emoticons/v1/112291/1.0', 'GlitchCat': 'https://static-cdn.jtvnw.net/emoticons/v1/304486301/1.0', 'GlitchLit': 'https://static-cdn.jtvnw.net/emoticons/v1/304489128/1.0', 'GlitchNRG': 'https://static-cdn.jtvnw.net/emoticons/v1/304489309/1.0', 'GoatEmotey': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_e41e4d6808224f25ae1fb625aa26de63/1.0', 'GoldPLZ': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_c1f4899e65cf4f53b2fd98e15733973a/1.0', 'GrammarKing': 'https://static-cdn.jtvnw.net/emoticons/v1/3632/1.0', 'GunRun': 'https://static-cdn.jtvnw.net/emoticons/v1/1584743/1.0', 'HSCheers': 'https://static-cdn.jtvnw.net/emoticons/v1/444572/1.0', 'HSWP': 'https://static-cdn.jtvnw.net/emoticons/v1/446979/1.0', 'HarleyWink': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_8b0ac3eee4274a75868e3d0686d7b6f7/1.0', 'HassaanChop': 'https://static-cdn.jtvnw.net/emoticons/v1/20225/1.0', 'HeyGuys': 'https://static-cdn.jtvnw.net/emoticons/v1/30259/1.0', 'HolidayCookie': 'https://static-cdn.jtvnw.net/emoticons/v1/1713813/1.0', 'HolidayLog': 'https://static-cdn.jtvnw.net/emoticons/v1/1713816/1.0', 'HolidayPresent': 'https://static-cdn.jtvnw.net/emoticons/v1/1713819/1.0', 'HolidaySanta': 'https://static-cdn.jtvnw.net/emoticons/v1/1713822/1.0', 'HolidayTree': 'https://static-cdn.jtvnw.net/emoticons/v1/1713825/1.0', 'HotPokket': 'https://static-cdn.jtvnw.net/emoticons/v1/357/1.0', 'HungryPaimon': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_535e40afa0b34a9481997627b1b47d96/1.0', 'ImTyping': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_b0c6ccb3b12b4f99a9cc83af365a09f1/1.0', 'IntersexPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827332/1.0', 'InuyoFace': 'https://static-cdn.jtvnw.net/emoticons/v1/160396/1.0', 'ItsBoshyTime': 'https://static-cdn.jtvnw.net/emoticons/v1/133468/1.0', 'JKanStyle': 'https://static-cdn.jtvnw.net/emoticons/v1/15/1.0', 'Jebaited': 'https://static-cdn.jtvnw.net/emoticons/v1/114836/1.0', 'Jebasted': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_031bf329c21040a897d55ef471da3dd3/1.0', 'JonCarnage': 'https://static-cdn.jtvnw.net/emoticons/v1/26/1.0', 'KAPOW': 'https://static-cdn.jtvnw.net/emoticons/v1/133537/1.0', 'KEKHeim': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_7c5d25facc384c47963d25a5057a0b40/1.0', 'Kappa': 'https://static-cdn.jtvnw.net/emoticons/v1/80393/1.0', 'KappaClaus': 'https://static-cdn.jtvnw.net/emoticons/v1/74510/1.0', 'KappaPride': 'https://static-cdn.jtvnw.net/emoticons/v1/55338/1.0', 'KappaRoss': 'https://static-cdn.jtvnw.net/emoticons/v1/70433/1.0', 'KappaWealth': 'https://static-cdn.jtvnw.net/emoticons/v1/81997/1.0', 'Kappu': 'https://static-cdn.jtvnw.net/emoticons/v1/160397/1.0', 'Keepo': 'https://static-cdn.jtvnw.net/emoticons/v1/1902/1.0', 'KevinTurtle': 'https://static-cdn.jtvnw.net/emoticons/v1/40/1.0', 'KingWorldCup': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_533b8c4a9f6e4bfbb528ad39974e3481/1.0', 'Kippa': 'https://static-cdn.jtvnw.net/emoticons/v1/1901/1.0', 'KomodoHype': 'https://static-cdn.jtvnw.net/emoticons/v1/81273/1.0', 'KonCha': 'https://static-cdn.jtvnw.net/emoticons/v1/160400/1.0', 'Kreygasm': 'https://static-cdn.jtvnw.net/emoticons/v1/41/1.0', 'LUL': 'https://static-cdn.jtvnw.net/emoticons/v1/425618/1.0', 'LaundryBasket': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_ecb0bfd49b3c4325864b948d46c8152b/1.0', 'Lechonk': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_665235901db747b1bd395a5f1c0ab8a9/1.0', 'LesbianPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827340/1.0', 'LionOfYara': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_adfadf0ae06a4258adc865761746b227/1.0', 'MVGame': 'https://static-cdn.jtvnw.net/emoticons/v1/142140/1.0', 'Mau5': 'https://static-cdn.jtvnw.net/emoticons/v1/30134/1.0', 'MaxLOL': 'https://static-cdn.jtvnw.net/emoticons/v1/1290325/1.0', 'MechaRobot': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_0be25a1663bd472495b91e0302cec166/1.0', 'MercyWing1': 'https://static-cdn.jtvnw.net/emoticons/v1/1003187/1.0', 'MercyWing2': 'https://static-cdn.jtvnw.net/emoticons/v1/1003189/1.0', 'MikeHogu': 'https://static-cdn.jtvnw.net/emoticons/v1/81636/1.0', 'MingLee': 'https://static-cdn.jtvnw.net/emoticons/v1/68856/1.0', 'ModLove': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_a2dfbbbbf66f4a75b0f53db841523e6c/1.0', 'MorphinTime': 'https://static-cdn.jtvnw.net/emoticons/v1/156787/1.0', 'MrDestructoid': 'https://static-cdn.jtvnw.net/emoticons/v1/28/1.0', 'MyAvatar': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_c0c9c932c82244ff920ad2134be90afb/1.0', 'NewRecord': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_53f6a6af8b0e453d874bbefee49b3e73/1.0', 'NiceTry': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_1f524be9838146e3bc9e529c17f797d3/1.0', 'NinjaGrumpy': 'https://static-cdn.jtvnw.net/emoticons/v1/138325/1.0', 'NomNom': 'https://static-cdn.jtvnw.net/emoticons/v1/90075/1.0', 'NonbinaryPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827356/1.0', 'NotATK': 'https://static-cdn.jtvnw.net/emoticons/v1/34875/1.0', 'NotLikeThis': 'https://static-cdn.jtvnw.net/emoticons/v1/58765/1.0', 'O.O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555572/1.0', 'O.o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555570/1.0', 'OSFrog': 'https://static-cdn.jtvnw.net/emoticons/v1/81248/1.0', 'O_O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555571/1.0', 'O_o': 'https://static-cdn.jtvnw.net/emoticons/v1/6/1.0', 'OhMyDog': 'https://static-cdn.jtvnw.net/emoticons/v1/81103/1.0', 'OneHand': 'https://static-cdn.jtvnw.net/emoticons/v1/66/1.0', 'OpieOP': 'https://static-cdn.jtvnw.net/emoticons/v1/100590/1.0', 'OptimizePrime': 'https://static-cdn.jtvnw.net/emoticons/v1/16/1.0', 'PJSalt': 'https://static-cdn.jtvnw.net/emoticons/v1/36/1.0', 'PJSugar': 'https://static-cdn.jtvnw.net/emoticons/v1/102556/1.0', 'PMSTwin': 'https://static-cdn.jtvnw.net/emoticons/v1/92/1.0', 'PRChase': 'https://static-cdn.jtvnw.net/emoticons/v1/28328/1.0', 'PanicVis': 'https://static-cdn.jtvnw.net/emoticons/v1/3668/1.0', 'PansexualPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827370/1.0', 'PartyHat': 'https://static-cdn.jtvnw.net/emoticons/v1/965738/1.0', 'PartyTime': 'https://static-cdn.jtvnw.net/emoticons/v1/135393/1.0', 'PeoplesChamp': 'https://static-cdn.jtvnw.net/emoticons/v1/3412/1.0', 'PermaSmug': 'https://static-cdn.jtvnw.net/emoticons/v1/27509/1.0', 'PicoMause': 'https://static-cdn.jtvnw.net/emoticons/v1/111300/1.0', 'PikaRamen': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_a25ad7124e584c949e2f63917e3d747a/1.0', 'PinkMercy': 'https://static-cdn.jtvnw.net/emoticons/v1/1003190/1.0', 'PipeHype': 'https://static-cdn.jtvnw.net/emoticons/v1/4240/1.0', 'PixelBob': 'https://static-cdn.jtvnw.net/emoticons/v1/1547903/1.0', 'PizzaTime': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_f202746ed88f4e7c872b50b1f7fd78cc/1.0', 'PogBones': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_30050f4353aa4322b25b6b044703e5d1/1.0', 'PogChamp': 'https://static-cdn.jtvnw.net/emoticons/v1/305954156/1.0', 'Poooound': 'https://static-cdn.jtvnw.net/emoticons/v1/117484/1.0', 'PopCorn': 'https://static-cdn.jtvnw.net/emoticons/v1/724216/1.0', 'PopGhost': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_cff32f43571543828847738e27acf4ef/1.0', 'PopNemo': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_5d523adb8bbb4786821cd7091e47da21/1.0', 'PoroSad': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_4c39207000564711868f3196cc0a8748/1.0', 'PotFriend': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_e02650251d204198923de93a0c62f5f5/1.0', 'PowerUpL': 'https://static-cdn.jtvnw.net/emoticons/v1/425688/1.0', 'PowerUpR': 'https://static-cdn.jtvnw.net/emoticons/v1/425671/1.0', 'PraiseIt': 'https://static-cdn.jtvnw.net/emoticons/v1/38586/1.0', 'PrimeMe': 'https://static-cdn.jtvnw.net/emoticons/v1/115075/1.0', 'PunOko': 'https://static-cdn.jtvnw.net/emoticons/v1/160401/1.0', 'PunchTrees': 'https://static-cdn.jtvnw.net/emoticons/v1/47/1.0', 'R)': 'https://static-cdn.jtvnw.net/emoticons/v1/14/1.0', 'R-)': 'https://static-cdn.jtvnw.net/emoticons/v1/555555600/1.0', 'RaccAttack': 'https://static-cdn.jtvnw.net/emoticons/v1/114870/1.0', 'RalpherZ': 'https://static-cdn.jtvnw.net/emoticons/v1/1900/1.0', 'RedCoat': 'https://static-cdn.jtvnw.net/emoticons/v1/22/1.0', 'ResidentSleeper': 'https://static-cdn.jtvnw.net/emoticons/v1/245/1.0', 'RitzMitz': 'https://static-cdn.jtvnw.net/emoticons/v1/4338/1.0', 'RlyTho': 'https://static-cdn.jtvnw.net/emoticons/v1/134256/1.0', 'RuleFive': 'https://static-cdn.jtvnw.net/emoticons/v1/107030/1.0', 'RyuChamp': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_0ebc590ba68447269831af61d8bc9e0d/1.0', 'SMOrc': 'https://static-cdn.jtvnw.net/emoticons/v1/52/1.0', 'SSSsss': 'https://static-cdn.jtvnw.net/emoticons/v1/46/1.0', 'SUBprise': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_fcbeed664f7c47d6ba3b57691275ef51/1.0', 'SabaPing': 'https://static-cdn.jtvnw.net/emoticons/v1/160402/1.0', 'SeemsGood': 'https://static-cdn.jtvnw.net/emoticons/v1/64138/1.0', 'SeriousSloth': 'https://static-cdn.jtvnw.net/emoticons/v1/81249/1.0', 'ShadyLulu': 'https://static-cdn.jtvnw.net/emoticons/v1/52492/1.0', 'ShazBotstix': 'https://static-cdn.jtvnw.net/emoticons/v1/87/1.0', 'Shush': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_819621bcb8f44566a1bd8ea63d06c58f/1.0', 'SingsMic': 'https://static-cdn.jtvnw.net/emoticons/v1/300116349/1.0', 'SingsNote': 'https://static-cdn.jtvnw.net/emoticons/v1/300116350/1.0', 'SmoocherZ': 'https://static-cdn.jtvnw.net/emoticons/v1/89945/1.0', 'SoBayed': 'https://static-cdn.jtvnw.net/emoticons/v1/1906/1.0', 'SoonerLater': 'https://static-cdn.jtvnw.net/emoticons/v1/2113050/1.0', 'Squid1': 'https://static-cdn.jtvnw.net/emoticons/v1/191762/1.0', 'Squid2': 'https://static-cdn.jtvnw.net/emoticons/v1/191763/1.0', 'Squid3': 'https://static-cdn.jtvnw.net/emoticons/v1/191764/1.0', 'Squid4': 'https://static-cdn.jtvnw.net/emoticons/v1/191767/1.0', 'StinkyCheese': 'https://static-cdn.jtvnw.net/emoticons/v1/90076/1.0', 'StinkyGlitch': 'https://static-cdn.jtvnw.net/emoticons/v1/304486324/1.0', 'StoneLightning': 'https://static-cdn.jtvnw.net/emoticons/v1/17/1.0', 'StrawBeary': 'https://static-cdn.jtvnw.net/emoticons/v1/114876/1.0', 'SuperVinlin': 'https://static-cdn.jtvnw.net/emoticons/v1/118772/1.0', 'SwiftRage': 'https://static-cdn.jtvnw.net/emoticons/v1/34/1.0', 'TBAngel': 'https://static-cdn.jtvnw.net/emoticons/v1/143490/1.0', 'TF2John': 'https://static-cdn.jtvnw.net/emoticons/v1/1899/1.0', 'TPFufun': 'https://static-cdn.jtvnw.net/emoticons/v1/508650/1.0', 'TPcrunchyroll': 'https://static-cdn.jtvnw.net/emoticons/v1/323914/1.0', 'TTours': 'https://static-cdn.jtvnw.net/emoticons/v1/38436/1.0', 'TakeNRG': 'https://static-cdn.jtvnw.net/emoticons/v1/112292/1.0', 'TearGlove': 'https://static-cdn.jtvnw.net/emoticons/v1/160403/1.0', 'TehePelo': 'https://static-cdn.jtvnw.net/emoticons/v1/160404/1.0', 'ThankEgg': 'https://static-cdn.jtvnw.net/emoticons/v1/160392/1.0', 'TheIlluminati': 'https://static-cdn.jtvnw.net/emoticons/v1/145315/1.0', 'TheRinger': 'https://static-cdn.jtvnw.net/emoticons/v1/18/1.0', 'TheTarFu': 'https://static-cdn.jtvnw.net/emoticons/v1/111351/1.0', 'TheThing': 'https://static-cdn.jtvnw.net/emoticons/v1/7427/1.0', 'ThunBeast': 'https://static-cdn.jtvnw.net/emoticons/v1/1898/1.0', 'TinyFace': 'https://static-cdn.jtvnw.net/emoticons/v1/111119/1.0', 'TombRaid': 'https://static-cdn.jtvnw.net/emoticons/v1/864205/1.0', 'TooSpicy': 'https://static-cdn.jtvnw.net/emoticons/v1/114846/1.0', 'TransgenderPride': 'https://static-cdn.jtvnw.net/emoticons/v1/307827377/1.0', 'TriHard': 'https://static-cdn.jtvnw.net/emoticons/v1/120232/1.0', 'TwitchConHYPE': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_13b6dd7f3a3146ef8dc10f66d8b42a96/1.0', 'TwitchLit': 'https://static-cdn.jtvnw.net/emoticons/v1/166263/1.0', 'TwitchRPG': 'https://static-cdn.jtvnw.net/emoticons/v1/1220086/1.0', 'TwitchSings': 'https://static-cdn.jtvnw.net/emoticons/v1/300116344/1.0', 'TwitchUnity': 'https://static-cdn.jtvnw.net/emoticons/v1/196892/1.0', 'TwitchVotes': 'https://static-cdn.jtvnw.net/emoticons/v1/479745/1.0', 'UWot': 'https://static-cdn.jtvnw.net/emoticons/v1/134255/1.0', 'UnSane': 'https://static-cdn.jtvnw.net/emoticons/v1/111792/1.0', 'UncleNox': 'https://static-cdn.jtvnw.net/emoticons/v1/114856/1.0', 'VirtualHug': 'https://static-cdn.jtvnw.net/emoticons/v1/301696583/1.0', 'VoHiYo': 'https://static-cdn.jtvnw.net/emoticons/v1/81274/1.0', 'VoteNay': 'https://static-cdn.jtvnw.net/emoticons/v1/106294/1.0', 'VoteYea': 'https://static-cdn.jtvnw.net/emoticons/v1/106293/1.0', 'WTRuck': 'https://static-cdn.jtvnw.net/emoticons/v1/114847/1.0', 'WholeWheat': 'https://static-cdn.jtvnw.net/emoticons/v1/1896/1.0', 'WhySoSerious': 'https://static-cdn.jtvnw.net/emoticons/v1/emotesv2_1fda4a1b40094c93af334f8b60868a7c/1.0', 'WutFace': 'https://static-cdn.jtvnw.net/emoticons/v1/28087/1.0', 'YouDontSay': 'https://static-cdn.jtvnw.net/emoticons/v1/134254/1.0', 'YouWHY': 'https://static-cdn.jtvnw.net/emoticons/v1/4337/1.0', 'bleedPurple': 'https://static-cdn.jtvnw.net/emoticons/v1/62835/1.0', 'cmonBruh': 'https://static-cdn.jtvnw.net/emoticons/v1/84608/1.0', 'copyThis': 'https://static-cdn.jtvnw.net/emoticons/v1/112288/1.0', 'duDudu': 'https://static-cdn.jtvnw.net/emoticons/v1/62834/1.0', 'imGlitch': 'https://static-cdn.jtvnw.net/emoticons/v1/112290/1.0', 'mcaT': 'https://static-cdn.jtvnw.net/emoticons/v1/35063/1.0', 'o.O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555574/1.0', 'o.o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555576/1.0', 'o_O': 'https://static-cdn.jtvnw.net/emoticons/v1/555555573/1.0', 'o_o': 'https://static-cdn.jtvnw.net/emoticons/v1/555555575/1.0', 'panicBasket': 'https://static-cdn.jtvnw.net/emoticons/v1/22998/1.0', 'pastaThat': 'https://static-cdn.jtvnw.net/emoticons/v1/112289/1.0', 'riPepperonis': 'https://static-cdn.jtvnw.net/emoticons/v1/62833/1.0', 'twitchRaid': 'https://static-cdn.jtvnw.net/emoticons/v1/62836/1.0'}


        print(channels)
        if auth=="1":
            users=db["TWITCH_TACHKA"].find_one({"type":"accs"})["tokens"]
            try:
                current_proxy=db["TWITCH_TACHKA"].find_one({"type":"proxy"})["current_proxy"][token]
            except:
                current_proxy="Отсутствует прокси"
            port=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["ports"][token]
            if db["TWITCH_TACHKA"].count_documents({"channel":channel})!=0:
                files=db["TWITCH_TACHKA"].find_one({"channel":channel})["files"]
                
                print(1)
                print(connections)
                
                
                #for i in range(1500):
                    #i1=random.choice(users)
                    #user=twitch_chat_irc.TwitchChatIRC(i1.split(":")[0],i1.split(":")[1]+":"+i1.split(":")[2])
            else:
                files=[]
            if channel not in connections:
                connections[channel]=[]
                users_connection[channel]=[]
            if not style:
                return templates.TemplateResponse("tachka.html",{"request":request,"emotes":global_emotions,"token":token,"channel":channel,"files":files,"count_users":(connections[channel]),"current_proxy":current_proxy,"port":port})
            else:
                return templates.TemplateResponse("old_tachka.html",{"request":request,"emotes":global_emotions,"token":token,"channel":channel,"files":files,"count_users":(connections[channel]),"current_proxy":current_proxy,"port":port})
        else:
            files=db["TWITCH_TACHKA"].find_one({"channel":channel})["files"]
            return templates.TemplateResponse("tachka_non_channel.html",{"request":request,"token":token,"channel":channel,"files":files})
    else:
        return templates.TemplateResponse("login.html",{"request":request})

@app.get("/twitch/pjs",response_class=HTMLResponse)
async def pjs(request: Request):
    return templates.TemplateResponse("p.html",{"request":request})



@app.get("/twitch/tachka_files",response_class=HTMLResponse)
async def get_tachka(request: Request,token:str):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<150 and token in channels:
        channel=channels[token]
        files=db["TWITCH_TACHKA"].find_one({"channel":channel})["files"]
        return templates.TemplateResponse("new_tachka_files.html",{"request":request,"token":token,"files":files})


@app.get("/twitch/new_task_follow",response_class=HTMLResponse)
async def task_follow(request: Request,token:str,count:int,kd:int):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<150 and token in channels:
        workers=db["TWITCH_TACHKA"].find_one({"type":"workers"})["workers"]
        for i in workers:
            if workers[i]=="1":
                workers[i]="0"
                print("Воркер для фоллов",i)
                db["TWITCH_TACHKA"].update_one({"type":"workers"},{"$set":{"workers":workers}})
                for i1 in range(int(count)):
                    await asyncio.sleep(1)
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"https://szhnserv.ru/twitch/follow?token={token}&port={i}"):
                            #print("+follow")
                            pass
                    await asyncio.sleep(int(kd))
                workers=db["TWITCH_TACHKA"].find_one({"type":"workers"})["workers"]
                workers[i]="1"
                db["TWITCH_TACHKA"].update_one({"type":"workers"},{"$set":{"workers":workers}})
        return f"Заказ на {count} фолловеров выполнен"

@app.get("/twitch/follow",response_class=HTMLResponse)
async def get_tachka(request: Request,token:str,port:str):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<80 and token in channels:
        channel=channels[token]
        users=db["TWITCH_TACHKA"].find_one({"type":"accs"})["tokens"][::-1]
        followers=db["TWITCH_TACHKA"].find_one({"channel":channel})["followers"]
        for i in users:
            if i not in followers:
                followers.append(i)
                
                token=i.split(":")[-1]
                
                            
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'http://szhnserv.ru:{port}/dwadawwadwaffawwaffwawafwafwafwafwaf/faesfasfaesfasefeasfasefasefasefeasfeasfeasfesafeasfeasfeasff323v3c423cdcecr32c432?channel={channel}&token={token}',timeout=8):
                            print("+")
                            await session.close()
                except Exception as e: print("Ошибка отправки",e)
                
                db["TWITCH_TACHKA"].update_one({"channel":channel},{"$set":{"followers":followers}})
                return "1"
                        
        

@app.post("/twitch/tachka/upload_files",response_class=RedirectResponse)
async def tach_files(request: Request,token:str=Form(),files: list[UploadFile] = File(...),channel:str=Form()):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<150 and token in channels:
        channel=channels[token]
        file_data = {}
        print(files)
    
        for file in files:
            contents = await file.read()
            file_data[file.filename] = contents.decode("utf-8")

        if db["TWITCH_TACHKA"].count_documents({"channel":channel})!=0:
            db["TWITCH_TACHKA"].update_one({"channel":channel},{"$set":{"files":file_data}})
        #db["TWITCH_TACHKA"].insert_one({"channel":channel,"files":file_data})
        return RedirectResponse(f"https://szhnserv.ru/twitch/tachka?token={token}&auth=1", status_code=status.HTTP_302_FOUND)


@app.post("/twitch/tachka/change_proxy")
async def change_proxy(request: Request,token:str=Form()):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<150 and token in channels:
        channel=channels[token]
        proxi=db["TWITCH_TACHKA"].find_one({"type":"proxy"})["proxy_list"]
        curr=db["TWITCH_TACHKA"].find_one({"type":"proxy"})["current_proxy"]
        for i in curr:
            if curr[i] in proxi:
                proxi.remove(curr[i])
        current_proxy=random.choice(proxi)
        print(current_proxy)
        curr[token]=current_proxy
        db["TWITCH_TACHKA"].update_one({"type":"proxy"},{"$set":{"current_proxy":curr}})
        return current_proxy.split("@")[1]


@app.post("/twitch/tachka",response_class=HTMLResponse)
async def go_tachka_msg(request: Request,token:str=Form(),msg:str=Form(),channel:str=Form()):
    channels=db["TWITCH_TACHKA"].find_one({"type":"tachka_tokens"})["chat_tokens"]
    if token and len(token)<150 and token in channels:
        channel=channels[token]
        
        
        irc_socket=random.choice(connections[channel])
        
        if ".txt" in msg:
            a=db["TWITCH_TACHKA"].find_one({"channel":channel})["files"]
            if msg in a:
                msg=random.choice(a[msg].split("\n"))
        irc_socket.send(bytes(f"PRIVMSG #{channel} :{msg}\r\n", "UTF-8"))
        #irc_socket.write(bytes(f"PRIVMSG #{channel} :{msg}\r\n", "UTF-8"))
        print("send",msg,"to",channel)
        







if __name__=='__main__':
    uvicorn.run("main:app",host="0.0.0.0",port=80,reload=False,workers=1)
