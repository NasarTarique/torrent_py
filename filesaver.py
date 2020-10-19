import hashlib
import settings
import asyncio

class FileSaver:

    def __init__(self):
        self.filepath = settings.FILE_PATH + settings.FILE_NAME

    async def checkfile(self):
        with open(self.filepath,"rb") as tfile:
            for x in range(0, len(settings.PIECES_HAVE)):
                tfile.seek(x*settings.TORR_DATA.piece_size)
                piece = tfile.read(settings.TORR_DATA.piece_size)
                piecehash = hashlib.sha1(piece).hexdigest()
                if(piecehash == settings.TORR_DATA.piece_hashes[x]):
                   settings.PIECES_HAVE[x] = '1'
                   settings.BAR.next()
                   

'''
    def write_piece(self,piece,pieceindex):
        try:
            with open(self.filepath,"r+b") as f:
                f.seek(pieceindex*settings.TORR_DATA.piece_size)
                f.write(piece)
        except IOError:
            with open(self.filepath, "w+b") as f:
                f.seek(pieceindex*settings.TORR_DATA.piece_size)
                f.write(piece)
'''
