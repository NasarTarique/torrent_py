import bencode
import sys
import random
import hashlib
from torrent_parser import parse_torrent_file
# import requests
import urllib.parse
import asyncio
import aiohttp
import struct
from math import ceil
import pdb
from torrinfo import TorrInfo

# Parse and Store data from torrent file

TORRENT_PATH = 'xubuntu-20.04.1-desktop-amd64.iso.torrent'
TORR_DATA = TorrInfo(TORRENT_PATH)
PIECES_HAVE = '0'*len(TORR_DATA.piece_hashes)
BlocksPerPiece = ceil(TORR_DATA.piece_size/16384)


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
        params = {
            'info_hash': TORR_DATA.info_hash,
            'peer_id': TORR_DATA.peer_id,
            'port': 6889,
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'compact': 0,
            'left': TORR_DATA.torrent_size - self.downloaded,
            'event': 'started',

        }

        return params

    def get_url(self):
        url = TORR_DATA.tracker_url + '?'+urllib.parse.urlencode(self.get_params())
        return url

    def connect(self):
        self.loop.run_until_complete(self.get_peers())

    async def decode_tracker_response(self):
        chunks = list(self.tracker_response['peers'])
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
            # print(self.tracker_response)
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
        # stores the length of the block downloaded from peer
        self.BlockLength = 0
        # Holds the index of the piece and block that needs to pe requested from the peer
        self.RequestPieceIndex = 0 
        self.RequestBlockIndex = 0

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
            info_hash, peer_id = await self.DecodeHandshakeMsg(peer_handshake)
            if secondmsg:
                print("this is the second msg")
                print("secondmsg")
                length, id, payload = await self.decodeMsg(secondmsg)
                if id==5:
                    self.DecodeBitfieldMsg(payload)
            else:
                reply = await self.Interested(reader, writer)
                await self.MessageHandler(reader, writer, reply)

            if(info_hash != self.torr_info.info_hash and peer_id!=self.host):
                await self.CloseConnection(writer)    
            else:
                check = await reader.read(10000)
                self.GetPieceIndex()
                for x in range(0, BlocksPerPiece, 1):
                    print(f"{x}")
                    await self.Request(reader, writer)
                    request_reply = await reader.read(65536) 
                    # print("request_reply")
                    await self.MessageHandler(reader, writer, request_reply)
                    print(f"Blocklength =============={self.BlockLength}")
                    self.downloaded_piece += self.Block
                    print(f"piece length {len(self.downloaded_piece)}")
                    print(TORR_DATA.piece_size)
                    if len(self.downloaded_piece) == TORR_DATA.piece_size:
                        # piec = self.downloaded_piece.decode()
                        with open("file.iso", "wb",2621440) as filewrite:
                            filewrite.write(self.downloaded_piece)
                        downloaded_piece_hashes = hashlib.sha1(self.downloaded_piece).hexdigest()
                        print(f"info hash {downloaded_piece_hashes}")
                        print(f"file info hash {TORR_DATA.piece_hashes[0]}")
                        if downloaded_piece_hashes == TORR_DATA.piece_hashes[0]:
                            print("matched")
 
                    self.Block = b'' 
                    self.BlockLength = 0
                    self.RequestBlockIndex += 16384


        except Exception as e:
            print(e)

    async def MessageHandler(self, reader, writer, msg):
        if len(msg) == 4:
            length = struct.unpack(">i", msg) if length == 0:
                pass
            else:
                await self.CloseConnection(writer)
        else:
            if len(msg) == 5:
                length, id = await self.decodeMsg(msg)
            else:
                length, id, payload = await self.decodeMsg(msg)
            

            if id == 0:
                await self.CloseConnection(writer)
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
                await self.CloseConnection(writer)

    async def CloseConnection(self, writer):
        writer.close()
        await writer.wait_closed()

    async def DecodeHandshakeMsg(self, msg):
        pstlen, pstr, reserved, info_hash, peer_id = struct.unpack(">1B19s8s20s20s", msg) 
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
    
    # get the index of the piece and block you need to request from peer
    def GetPieceIndex(self):
        for x in range(0, len(self.torr_info.piece_hashes)):
            if self.peer_pieces == '1' and PIECES_HAVE == '0':
                self.RequestPieceIndex = x
                break

    async def Request(self, reader, writer):
        request_msg = struct.pack(">iBiii", 13, 6, self.RequestPieceIndex, self.RequestBlockIndex, 16384)
        writer.write(request_msg)

    async def BlockMsg(self, reader, writer, msg):
        length, id, payload = await self.decodeMsg(msg)
        self.DecodePieceMsg(payload[0])
        while True:
            blockparts = await reader.read(65536)
            self.BlockLength += len(blockparts)
            if self.RequestBlockIndex == 31:
                break
            if self.BlockLength < 16384:
                self.Block += blockparts 
                print("Blocklength <")
                # print(blockparts)
            elif self.BlockLength == 16384:
                print("BlockLength =")
                self.Block += blockparts
                # print(blockparts)
                break
            else:
                break
        
    async def decodeMsg(self, msg):
        load_length, id = struct.unpack(">iB", msg[0:5])
        print(load_length)
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
        print(f"BLock offset =  {block} index = {index}")
        block_data = payload[8:len(payload)]
        self.BlockLength += len(block_data)
        self.Block += block_data
        print("initial Block data")


'''class  ManagePeers:

    def __init__(self,TorrInfo, Tracker):
        self.torr_info = TorrInfo
        self.pieces_have = [0]*len(TorrInfo.piece_hashes)
        self.Tracker = Tracker
'''


def main():
    t = Tracker()
    t.connect()

    peer_list = t.peer_list
    for x in range(0, len(peer_list), 1):
        P = Peer_Messaging(peer_list[x][0], peer_list[x][1], TORR_DATA)
        P.allowhandshake()


if __name__ == '__main__':
    main()
