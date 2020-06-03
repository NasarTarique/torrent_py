import bencode
import random
import hashlib
from torrent_parser import parse_torrent_file
import requests
import urllib.parse
import asyncio
import aiohttp
import sys


class TorrInfo:
    def __init__(self):
        self.file = {}
        self.info_hash: str = ''
        self.peer_id: str = ''
        self.parsed_torrent = {}
        self.torrent_size: int = 0
        self.tracker_url : str = ''
        self.total_pieces: int = 0
        self.piece_size: int = 0


    def get_torr_info(self, file_path):
        with open(file_path, 'rb') as f:
            meta_info = f.read()
            torrent = bencode.decode(meta_info)
        
        self.file = torrent

        self.info_hash = hashlib.sha1(bencode.bencode(torrent[b"info"])).digest()

        self.peer_id = '-PC0001-' + ''.join([str(random.randint(0, 9)) for _ in range(12)])

        self.parsed_torrent = parse_torrent_file(file_path)

        self.torrent_size = self.parsed_torrent['info']['length']

        self.tracker_url = self.parsed_torrent['announce']

        self.total_pieces = self.parsed_torrent['info']['pieces']

        self.piece_size = self.parsed_torrent['info']['piece length']


class Tracker:

    def  __init__(self):
        self.loop = asyncio.get_event_loop()
        self.uploaded: int =0
        self.downloaded: int  =0
        self.url = self.get_url()
        self.params = self.get_params()
        self.tracker_response = {}
        self.peer_list = []

    
    def get_params(self):
        torrent = TorrInfo()
        torrent.get_torr_info('xubuntu-20.04-desktop-amd64.iso.torrent')
        params={
            'info_hash':torrent.info_hash,
            'peer_id':torrent.peer_id,
            'port':6889,
            'uploaded':self.uploaded,
            'downloaded':self.downloaded,
            'compact':1,
            'left':torrent.torrent_size - self.downloaded,
            'event':'started'
        }

        return params

    
    def get_url(self):
        torrent = TorrInfo()
        torrent.get_torr_info('xubuntu-20.04-desktop-amd64.iso.torrent')
        url = torrent.tracker_url + '?'+urllib.parse.urlencode(self.get_params())
        return url

    def connect(self):
        self.loop.run_until_complete(self.get_peers())
        torrent = TorrInfo()
        torrent.get_torr_info('xubuntu-20.04-desktop-amd64.iso.torrent')
        response = requests.get(url=torrent.tracker_url,params=self.get_params())
        print("connect")
        list_peers = bencode.decode(response.content)
        print(list_peers[b'peers'])

    

    async def decode_tracker_response(self):
        chunks = [ self.tracker_response[b'peers'][x] for x in self.tracker_response[b'peers']]
        peers_enc = [chunks[x:x+6] for x in range(0,len(chunks),6)]

        for peer in peers_enc:
                h = [str(integer) for integer in peer[0:4]]
                host = '.'.join(h)
                print(host)
                peer_port = int(str(peer[4]) + str(peer[5]))
                print(peer_port)
                tup =(host, peer_port)
                self.peer_list.append(tup)
        
        

    async def get_peers(self):
        async with aiohttp.ClientSession() as  Session:
            response = await self.fetch(Session)
            self.tracker_response = bencode.decode(response)
            await self.decode_tracker_response()


    async def fetch(self,session):
        async with session.get(self.url) as response:
            return await response.content.read()



class Peer:

    def __init__(self,host, peer_port,torr_info):
        self.torr_info = torr_info
        self.host = host
        self.peer_port = peer_port
        self.peer_choking = True
        self.am_interested =  False
        self.loop = asyncio.get_event_loop()
        self.Handshake_msg = self.get_handshake_msg()

    
    def get_handshake_msg(self):
        handshake_msg = b''.join([(chr(19).encode()), b'BitTorrent protocol', (chr(0) * 8).encode(), self.torr_info.info_hash, self.torr_info.peer_id.encode() ])
        return handshake_msg
        
    def allowhandshake(self):
        self.loop.run_until_complete(self.Handshake())

    async def Handshake(self):
        try:
            reader, writer = await asyncio.open_connection(self.host, self.peer_port)
            writer.write(self.Handshake_msg)
            
            peer_handshake  =  await reader.read(1000)
            
            print(peer_handshake)
        except Exception as e:
            print(e)




    




def main():
    t = Tracker()
    t.connect()
    torr_info = TorrInfo()
    torr_info.get_torr_info('xubuntu-20.04-desktop-amd64.iso.torrent')
    peer_list = t.peer_list
    for x in range(0, len(peer_list),1 ):
        P = Peer(peer_list[0][0],peer_list[0][1], torr_info )
        P.allowhandshake()

   #  chunks = [t.tracker_response[b'peers'][x] for x in t.tracker_response[b'peers']]
   #  peer_list = [chunks[x:x+6] for x in range(0,len(chunks),6)]
   #  print(peer_list[0]) 

if  __name__ == '__main__':
    main()


# test 
# def main():
#     torrent = TorrInfo()
#     torrent.get_torr_info('xubuntu-20.04-desktop-amd64.iso.torrent')
#     url  = torrent.tracker_url
#     uploaded: int =0
#     downloaded: int = 0
#     first: bool = None
# 
#     params ={
#         'info_hash':torrent.info_hash,
#         'peer_id':torrent.peer_id,
#         'port': 6889,
#         'uploaded': uploaded,
#         'downloaded': downloaded,
#         'compact': 1,
#         'left': torrent.torrent_size - downloaded,
#         'event': 'started'
# 
#     }
#     
#     resp = requests.get(url,params)
#     response = resp.content
#     print(response)
#     print(bencode.decode(response))
# 
# 
# if __name__ == '__main__':
#     main()


# class Peer:
#     def __init__(self, torrent_info = TorrInfo('xubuntu-20.04-desktop-amd64.iso.torrent')):



