import bencode
import sys
import random
import hashlib
from torrent_parser import parse_torrent_file
import requests
import urllib.parse
import asyncio
import aiohttp
import struct

#Parse and Store data from torrent file



class TorrInfo:
    def __init__(self):
        self.file = {}
        self.info_hash: str = ''
        self.peer_id: str = ''
        self.parsed_torrent = {}
        self.torrent_size: int = 0
        self.tracker_url: str = ''
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

# Connect to Tracker & parse tracker response

class Tracker:

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.uploaded: int = 0
        self.downloaded: int = 0
        self.url = self.get_url()
        self.params = self.get_params()
        self.tracker_response = {}
        self.peer_list = []

    def get_params(self):
        torrent = TorrInfo()
        torrent.get_torr_info('xubuntu-20.04-desktop-amd64.iso.torrent')
        params = {
            'info_hash': torrent.info_hash,
            'peer_id': torrent.peer_id,
            'port': 6889,
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'compact': 0,
            'left': torrent.torrent_size - self.downloaded,
            'event': 'started',

        }

        return params

    def get_url(self):
        torrent = TorrInfo()
        torrent.get_torr_info('xubuntu-20.04-desktop-amd64.iso.torrent')
        url = torrent.tracker_url + '?'+urllib.parse.urlencode(self.get_params())
        return url

    def connect(self):
        self.loop.run_until_complete(self.get_peers())

    async def decode_tracker_response(self):
        chunks = list(self.tracker_response[b'peers'])
        peers_enc = [chunks[x:x+6] for x in range(0,len(chunks),6)]

        for peer in peers_enc:
            h = [str(integer) for integer in peer[0:4]]
            host = '.'.join(h)
            peer_port = peer[4]*256 + peer[5]
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


#Manage Peers
# Handshake ,keep alive , choke ,unchoke, interested , not interestes, have ,bitfield,request, piece,cancel, port
class Peer_Messaging:

    def __init__(self,host, peer_port,torr_info):
        self.torr_info = torr_info
        self.host = host
        self.peer_port = peer_port
        self.peer_choking = True
        self.am_interested = False
        self.peer_pieces = []
        self.loop = asyncio.get_event_loop()
        self.Block = b'' 
        self.downloaded_piece = b''
        self.blocklist = []
        self.BlockLength = 0

    async def Handshake(self, writer,reader):
        handshake_msg = b''.join([(chr(19).encode()), b'BitTorrent protocol', (chr(0) * 8).encode(), self.torr_info.info_hash, self.torr_info.peer_id.encode() ])
        writer.write(handshake_msg)
        return await reader.read(1000)

    def allowhandshake(self):
        self.loop.run_until_complete(self.ConnectPeer())

    async def ConnectPeer(self):
        try:
            reader, writer = await asyncio.open_connection(self.host, self.peer_port)

            peer_handshake = await self.Handshake(writer, reader)
            secondmsg = await reader.read(1000)
            print(peer_handshake)
            info_hash, peer_id = await self.DecodeHandshakeMsg(peer_handshake)
            if secondmsg:
                print("this is the second msg")
                print(secondmsg)
                length, id, payload = await self.decodeMsg(secondmsg)
                if id==5:
                    self.DecodeBitfieldMsg(payload)
            else:
                reply = await self.Interested(reader, writer)
                await self.MessageHandler(reader, writer, reply)

            if(info_hash != self.torr_info.info_hash and peer_id!=self.host):
                await self.CloseConnection(reader, writer)    
            else:
                check = await reader.read(10000)
                print(check)
                await self.Request(reader, writer)
                request_reply = await reader.read(65536)
                print(request_reply)
                await self.MessageHandler(reader, writer, request_reply)

        except Exception as e:
            print(e)

    async def MessageHandler(self, reader, writer, msg):
        print("jaja")
        if len(msg) == 4:
            print("yo")
            length = struct.unpack(">i", msg)
            if length == 0:
                pass
            else:
                await self.CloseConnection(reader, writer)
        else:
            if len(msg) == 5:
                length, id = await self.decodeMsg(msg)
            else:
                length, id, payload = await self.decodeMsg(msg)
            

            if id == 0:
                await self.CloseConnection(reader, writer)
            elif id == 1:
                await self.Interested(reader, writer)
            elif id == 2:
                pass
            elif id == 3:
                pass
            elif id == 4:
                pass
            elif id == 5:
                self.DecodeBitfieldMsg(payload[0])
            elif id == 6:
                pass
            elif id == 7:
                await self.BlockMsg(reader, writer, msg)
            else:
                await self.CloseConnection(reader, writer)

    async def CloseConnection(self, reader, writer):
        writer.close()
        reader.close()
        await writer.wait_closed()
        await reader.wait_closed()

    async def DecodeHandshakeMsg(self, msg):
        print(len(msg))
        pstlen, pstr, reserved, info_hash, peer_id = struct.unpack(">1B19s8s20s20s", msg) 
        print(f"{pstlen} ,{pstr}, {reserved} ,{info_hash}, {peer_id.decode()}")
        return info_hash, peer_id.decode()

    async def Interested(self, reader, writer):
        interested_msg = b''.join([((chr(0)*3)+chr(1)).encode(), (chr(2)).encode()])
        writer.write(interested_msg)
        return await reader.read(1000)

    async def Unchoke(self, reader, writer):
        unchoke_msg = b''.join([((chr(0)*3)+chr(1)).encode(), (chr(1)).encode()])
        writer.write(unchoke_msg)
        return await reader.read(1000)

    async def KeepAlive(self, writer):
        keep_alive_msg = b''.join([(chr(0)*4).encode()])
        writer.write(keep_alive_msg)

    async def Choke(self, reader, writer):
        choke_msg = b''.join([((chr(0)*3)+chr(1)).encode(), (chr(0)).encode()])
        writer.write(choke_msg)

    async def NotInterested(self, reader, writer):
        not_interested_msg = b''.join([((chr(0)*3)+chr(1)).encode(), (chr(3)).encode()])
        writer.write(not_interested_msg)
   
    async def Request(self, reader, writer):
        index = 0
        for x in range(0, len(self.torr_info.total_pieces)):
            if self.peer_pieces[x] == '1' and PIECES_HAVE[x] == '0':
                index = x
                break
        request_msg = struct.pack(">iBiii", 13, 6, 0, 0, 16384)
        writer.write(request_msg)

    async def BlockMsg(self, reader, writer, msg):
        length, id, payload = await self.decodeMsg(msg)
        self.DecodePieceMsg(payload[0])
        while True:
            blockparts = await reader.read(65536)
            self.BlockLength += len(blockparts)
            if self.BlockLength <= 16384:
                self.Block += blockparts
                print(blockparts)
                if len(blockparts) == 0:
                    print(len(self.Block))
                    break
        
    async def decodeMsg(self, msg):
        load_length, id = struct.unpack(">iB", msg[0:5])
        if len(msg) >= 6:
            load = struct.unpack(f">{len(msg)-5}s", msg[5:len(msg)])
            return load_length, id, load
        else:
            return load_length, id
    
    def DecodeBitfieldMsg(self, payload):
        self.peer_pieces = ''.join([bin(byte)[2:] for byte in payload[0]])
        print(self.peer_pieces[0])
    
    def DecodePieceMsg(self, payload):
        index, block = struct.unpack(">ii", payload[0:8])
        block_data = payload[8:len(payload)]
        self.BlockLength += len(block_data)
        self.Block += block_data
        print(block_data)


'''class  ManagePeers:

    def __init__(self,TorrInfo, Tracker):
        self.torr_info = TorrInfo
        self.pieces_have = [0]*len(TorrInfo.total_pieces)
        self.Tracker = Tracker
'''


TORR_DATA = TorrInfo()
TORR_DATA.get_torr_info('xubuntu-20.04-desktop-amd64.iso.torrent')
PIECES_HAVE = '0'*len(TORR_DATA.total_pieces)
print(f"PIECES_HAVE:::::::::::::::::::::::::::::::::::::::{PIECES_HAVE}")


def main():
    t = Tracker()
    t.connect()
    torr_info = TorrInfo()
    torr_info.get_torr_info('xubuntu-20.04-desktop-amd64.iso.torrent')

    peer_list = t.peer_list
    for x in range(0, len(peer_list), 1):
        P = Peer_Messaging(peer_list[x][0], peer_list[x][1], torr_info)
        P.allowhandshake()


if __name__ == '__main__':
    main()
