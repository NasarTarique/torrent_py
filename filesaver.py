
class FileSaver:

    def __init__(self):


    def write_piece(self,piece,pieceindex):
        try:
            with open((FILE_PATH+FILE_NAME),"r+b") as f:
                f.seek(pieceindex*settings.TORR_DATA.piece_size)
                f.write(piece)
        except IOException:
            with open((FILE_PATH+FILE_NAME), "w+b") as f:
                f.seek(pieceindex*settings.TORR_DATA.piece_size)
                f.write(piece)

        
