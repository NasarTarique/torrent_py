from settings import PIECES_HAVE, TORR_DATA

class Piece:

    def __init__(self):
        self.Block = b''
        self.downloaded_piece = b''
        self.RequestPieceIndex = 0
        self.RequestBlockOffset = 0
        self.blocklist = []
        self.BlockLength = 0

    def GetPieceIndex(self, peer_pieces):
        for x in range(0, len(TORR_DATA.piece_hashes)):
            if peer_pieces == '1' and PIECES_HAVE[x] == '0':
                self.RequestPieceIndex = x
                break
