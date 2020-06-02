import  sys
import asyncio
import aiohttp
from peer import  Tracker,Peer


class Client:

    def __init__(self,tracker_obj,Peer_obj):
        self.tracker = tracker_obj
        self.Peer = Peer_obj
        self.ClientSession =  aiohttp.ClientSession()
        self.queue = asyncio.Queue()


async def download(torrent_file):
    # read and parse torrent file
    torrent = read_torrent(torrent_file)

    # get the peers from tracker
    peer_addresses = await getr_peers(torrent)

    
    file_pieces_queue = asyncio.Queue()

    file_saver = FileSaver(file_pieces_queue)

    peers = [Peer(addr,file_pieces_queue) for addr in peer_addresses]


    await asyncio.gather(
        *([peer.download() for peer in peers] +
         [file_saver.start()])
    )

