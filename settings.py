from torrinfo import TorrInfo
from math import ceil

TORRENT_PATH = 'xubuntu-20.04.1-desktop-amd64.iso.torrent'
TORR_DATA = TorrInfo(TORRENT_PATH)
PIECES_HAVE = list('0'*len(TORR_DATA.piece_hashes))
MAX_PEERS = 50
CONNECTED_PEERS = 0
BlocksPerPiece = ceil(TORR_DATA.piece_size/16384)
FILE_PATH = ''
FILE_NAME = 'xubuntu-20.04.1-desktop-amd64.iso'
