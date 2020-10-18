import bencode
import hashlib
import urllib.parse
import asyncio
import aiohttp
import struct
import settings


class Tracker:

    def __init__(self):
        self.uploaded: int = 0
        self.downloaded: int = 0
        self.url = self.get_url()
        self.params = self.get_params()
        self.tracker_response = {}
        self.peer_list = []

    def get_params(self):
        params = {
            'info_hash': settings.TORR_DATA.info_hash,
            'peer_id': settings.TORR_DATA.peer_id,
            'port': 6889, 'uploaded': self.uploaded, 'downloaded': self.downloaded,
            'compact': 0,
            'left': settings.TORR_DATA.torrent_size - self.downloaded,
            'event': 'started',

        }

        return params

    def get_url(self):
        url = settings.TORR_DATA.tracker_url + '?'+urllib.parse.urlencode(self.get_params())
        return url

    async def decode_tracker_response(self, queue):
        chunks = list(self.tracker_response['peers'])
        peers_enc = [chunks[x:x+6] for x in range(0,len(chunks),6)]

        for peer in peers_enc:
            h = [str(integer) for integer in peer[0:4]]
            host = '.'.join(h)
            peer_port = peer[4]*256 + peer[5]
            tup = (host, peer_port)
            queue.put_nowait(tup)

    async def get_peers(self, queue):
        connection_trials = 0
        while True:
                async with aiohttp.ClientSession() as Session:
                    try:
                        response = await self.fetch(Session)
                        self.tracker_response = bencode.decode(response)
                        await self.decode_tracker_response(queue)
                        await asyncio.sleep(30)
                        if "0" not in settings.PIECES_HAVE and "2" not in settings.PIECES_HAVE:
                            break
                        connection_trials = 0
                    except Exception:
                        connection_trials+=1
                        print("Tracker Exception")

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
                for x in range(0, settings.BlocksPerPiece, 1):
                    print(f"{x}")
                    await self.Request(reader, writer)
                    request_reply = await reader.read(65536) 
                    # print("request_reply")
                    await self.MessageHandler(reader, writer, request_reply)
                    print(f"Blocklength =============={self.BlockLength}")
                    self.downloaded_piece += self.Block
                    print(f"piece length {len(self.downloaded_piece)}")
                    print(settings.TORR_DATA.piece_size)
                    if len(self.downloaded_piece) == settings.TORR_DATA.piece_size:
                        downloaded_piece_hashe = hashlib.sha1(self.downloaded_piece).hexdigest()
                        if downloaded_piece_hashe == settings.TORR_DATA.piece_hashes[self.RequestPieceIndex]:
                            print("matched")
                            settings.PIECES_HAVE[self.RequestPieceIndex] = '1'
                            self.write_piece(self.downloaded_piece)
                            break
                        else:
                            settings.PIECES_HAVE[self.RequestPieceIndex] = '0'
                            break
                    self.Block = b'' 
                    self.BlockLength = 0
                    self.RequestBlockIndex += 16384

        except Exception as e:
            settings.PIECES_HAVE[self.RequestPieceIndex] = '0'
            print(f"Exception Consumed {e}")

    async def MessageHandler(self, reader, writer, msg):
        if len(msg) == 4:
            length = struct.unpack(">i", msg)
            if length == 0: pass
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
            if self.peer_pieces[x] == '1' and settings.PIECES_HAVE[x] == '0':
                self.RequestPieceIndex = x
                settings.PIECES_HAVE[x] = '2'
                break

    async def Request(self, reader, writer):
        request_msg = struct.pack(">iBiii", 13, 6, self.RequestPieceIndex, self.RequestBlockIndex, 16384)
        writer.write(request_msg)
        
    def write_piece(self,piece):
        try:
            with open((settings.FILE_PATH+settings.FILE_NAME),"r+b") as f:
                f.seek(self.RequestPieceIndex*settings.TORR_DATA.piece_size)
                byteoffset = self.RequestPieceIndex*settings.TORR_DATA.piece_size
                print(f"byteoffset = {byteoffset}")
                f.write(piece)
        except IOError:
            with open((settings.FILE_PATH+settings.FILE_NAME), "w+b") as f:
                f.seek(self.RequestPieceIndex*settings.TORR_DATA.piece_size)
                byteoffset = self.RequestPieceIndex*settings.TORR_DATA.piece_size
                print(f"byteoffset = {byteoffset}")
                f.write(piece)

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


