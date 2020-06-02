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
       #  response = requests.get(url=torrent.tracker_url,params=self.get_params())
       #  print("connect")
       #  print(response)


    async def get_peers(self):
        async with aiohttp.ClientSession() as  Session:
            response = await self.fetch(Session)
            self.tracker_response = bencode.decode(response)
            
    

    async def fetch(self,session):
        async with session.get(self.url) as response:
            return await response.content.read()





def main():
    t = Tracker()
    t.connect()
    chunks = [t.tracker_response[b'peers'][x] for x in t.tracker_response[b'peers']]
    peer_list = [chunks[x:x+6] for x in range(0,len(chunks),6)]
    print(peer_list[0]) 

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



