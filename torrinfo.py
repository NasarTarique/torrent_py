import bencode 
import random
import hashlib
from torrent_parser import parse_torrent_file


TORRENT_PATH = 'xubuntu-20.04.1-desktop-amd64.iso.torrent'

class TorrInfo:
    def __init__(self,torrentpath):
        self.file = {}
        self.info_hash: str = ''
        self.peer_id: str = ''
        self.parsed_torrent = {}
        self.torrent_size: int = 0
        self.tracker_url: str = ''
        self.piece_hashes = [] 
        self.piece_size: int = 0
        self.get_torr_info(torrentpath)

    def get_torr_info(self, file_path):
        with open(file_path, 'rb') as f:
            meta_info = f.read()
            torrent = bencode.decode(meta_info)

        self.file = torrent
        self.info_hash = hashlib.sha1(bencode.bencode(torrent["info"])).digest()
        self.peer_id = '-PC0001-' + ''.join([str(random.randint(0, 9)) for _ in range(12)])
        self.parsed_torrent = parse_torrent_file(file_path)
        self.torrent_size = self.parsed_torrent['info']['length']
        self.tracker_url = self.parsed_torrent['announce']
        self.piece_hashes += self.parsed_torrent['info']['pieces']
        self.piece_size = self.parsed_torrent['info']['piece length']
