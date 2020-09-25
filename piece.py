class Piece:

    def __init__(self):
        self.Block = b''
        self.downloaded_piece = b''
        self.RequestPieceIndex = 0
        self.RequestBlockOffset = 0
        self.blocklist = []
        self.BlockLength = 0

    def GetPieceIndex(self):
        for x in range(0, len(self.torr_info.piece_hashes)):
            if self.peer_pieces == '1' and PIECES_HAVE == '0':
                self.RequestPieceIndex = x
                break
