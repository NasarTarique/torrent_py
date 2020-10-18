import peertest
import settings
import asyncio
import filesaver

maxpeers = settings.MAX_PEERS
         

async def download(queue):
    while True:
        peer_addr = await queue.get()
        PeerObj = peertest.Peer_Messaging(peer_addr[0],peer_addr[1], settings.TORR_DATA)
        await PeerObj.ConnectPeer()


async def main():
    fsobj = filesaver.FileSaver()
    fsobj.checkfile()
    queue = asyncio.Queue()
    t = peertest.Tracker()
    tracker_task = asyncio.create_task(t.get_peers(queue))
    Downloader = [asyncio.create_task(download(queue)) for x in range(0, maxpeers, 1)] 
    await asyncio.gather(tracker_task)


if __name__ == '__main__':
    asyncio.run(main())
