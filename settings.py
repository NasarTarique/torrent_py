from torrinfo import TorrInfo
from math import ceil
from asyncio import Queue
from progress.bar import ShadyBar

print('''
      
  ______                           __     ____
 /_  __/___  _____________  ____  / /_   / __ \__  __
  / / / __ \/ ___/ ___/ _ \/ __ \/ __/  / /_/ / / / /
 / / / /_/ / /  / /  /  __/ / / / /_   / ____/ /_/ /
/_/  \____/_/  /_/   \___/_/ /_/\__/  /_/    \__, /
                                            /____/
      ''')

TORRENT_PATH = 'xubuntu-20.04.1-desktop-amd64.iso.torrent'
TORR_DATA = TorrInfo(TORRENT_PATH)
PIECES_HAVE = list('0'*len(TORR_DATA.piece_hashes))
MAX_PEERS = 50
CONNECTED_PEERS = 0
PIECES_DOWNLOADED = 0
PIECE_Q = Queue()
BlocksPerPiece = ceil(TORR_DATA.piece_size/16384)
FILE_PATH = ''
FILE_NAME = 'xubuntu-20.04.1-desktop-amd64.iso'
BAR = ShadyBar(f'Downloading {FILE_NAME} ..', max=len(PIECES_HAVE), suffix='%(percent)d%%')
