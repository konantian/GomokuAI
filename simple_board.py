
"""
simple_board.py

Implements a basic Go board with functions to:
- initialize to a given board size
- check if a move is legal
- play a move

The board uses a 1-dimensional representation with padding
"""
import random
import numpy as np
from board_util import GoBoardUtil, BLACK, WHITE, EMPTY, BORDER, \
                       PASS, is_black_white, coord_to_point, where1d, \
                       MAXSIZE, NULLPOINT

from gtp_connection import point_to_coord,format_point

class SimpleGoBoard(object):

    def get_color(self, point):
        try:
            return self.board[point]
        except:
            return 3

    def pt(self, row, col):
        return coord_to_point(row, col, self.size)

    def is_legal(self, point, color):
        """
        Check whether it is legal for color to play on point
        """
        assert is_black_white(color)
        # Special cases
        if point == PASS:
            return True
        elif self.board[point] != EMPTY:
            return False
        if point == self.ko_recapture:
            return False
            
        # General case: detect captures, suicide
        opp_color = GoBoardUtil.opponent(color)
        self.board[point] = color
        legal = True
        has_capture = self._detect_captures(point, opp_color)
        if not has_capture and not self._stone_has_liberty(point):
            block = self._block_of(point)
            if not self._has_liberty(block): # suicide
                legal = False
        self.board[point] = EMPTY
        return legal

    def get_empty_points(self):
        """
        Return:
            The empty points on the board
        """
        return where1d(self.board == EMPTY)

    def _on_board_neighbors(self, point):
        nbs = []
        for nb in self._neighbors(point):
            if self.board[nb] != BORDER:
                nbs.append(nb)
        return nbs

    def _initialize_neighbors(self):
        """
        precompute neighbor array.
        For each point on the board, store its list of on-the-board neighbors
        """
        self.neighbors = []
        for point in range(self.maxpoint):
            if self.board[point] == BORDER:
                self.neighbors.append([])
            else:
                self.neighbors.append(self._on_board_neighbors(point))

    def __init__(self, size):
        """
        Creates a Go board of given size
        """
        assert 2 <= size <= MAXSIZE
        self.reset(size)
        self.moves=[]
        self.last_move = None

    def reset(self, size):
        """
        Creates a start state, an empty board with the given size
        The board is stored as a one-dimensional array
        See GoBoardUtil.coord_to_point for explanations of the array encoding
        """
        self.size = size
        self.NS = size + 1
        self.WE = 1
        self.ko_recapture = None
        self.current_player = BLACK
        self.maxpoint = size * size + 3 * (size + 1)
        self.board = np.full(self.maxpoint, BORDER, dtype = np.int32)
        self.liberty_of = np.full(self.maxpoint, NULLPOINT, dtype = np.int32)
        self._initialize_empty_points(self.board)
        self._initialize_neighbors()
        self.moves=[]
        self.last_move = None

    def copy(self):
        b = SimpleGoBoard(self.size)
        assert b.NS == self.NS
        assert b.WE == self.WE
        b.ko_recapture = self.ko_recapture
        b.current_player = self.current_player
        assert b.maxpoint == self.maxpoint
        b.board = np.copy(self.board)
        return b

    def row_start(self, row):
        assert row >= 1
        assert row <= self.size
        return row * self.NS + 1
        
    def _initialize_empty_points(self, board):
        """
        Fills points on the board with EMPTY
        Argument
        ---------
        board: numpy array, filled with BORDER
        """
        for row in range(1, self.size + 1):
            start = self.row_start(row)
            board[start : start + self.size] = EMPTY

    def neighbors_of_color(self, point, color):
        """ List of neighbors of point of given color """
        nbc = []
        for nb in self.neighbors[point]:
            if self.get_color(nb) == color:
                nbc.append(nb)
        return nbc
        
    def find_neighbor_of_color(self, point, color):
        """ Return one neighbor of point of given color, or None """
        for nb in self.neighbors[point]:
            if self.get_color(nb) == color:
                return nb
        return None
        
    def _neighbors(self, point):
        """ List of all four neighbors of the point """
        return [point - 1, point + 1, point - self.NS, point + self.NS]

    def _diag_neighbors(self, point):
        """ List of all four diagonal neighbors of point """
        return [point - self.NS - 1, 
                point - self.NS + 1, 
                point + self.NS - 1, 
                point + self.NS + 1]
    
    def _point_to_coord(self, point):
        """
        Transform point index to row, col.
        
        Arguments
        ---------
        point
        
        Returns
        -------
        x , y : int
        coordination of the board  1<= x <=size, 1<= y <=size .
        """
        if point is None:
            return 'pass'
        row, col = divmod(point, self.NS)
        return row, col

    def is_legal_gomoku(self, point, color):
        """
            Check whether it is legal for color to play on point, for the game of gomoku
            """
        return self.board[point] == EMPTY
    
    def play_move_gomoku(self, point, color):
        """
            Play a move of color on point, for the game of gomoku
            Returns boolean: whether move was legal
            """
        assert is_black_white(color)
        assert point != PASS
        if self.board[point] != EMPTY:
            return False
        self.board[point] = color
        self.moves.append(point)
        self.last_move = point
        self.current_player = GoBoardUtil.opponent(color)
        return True
        
    def _point_direction_check_connect_gomoko(self, point, shift):
        """
        Check if the point has connect5 condition in a direction
        for the game of Gomoko.
        """
        color = self.board[point]
        count = 1
        d = shift
        p = point
        while True:
            p = p + d
            if self.board[p] == color:
                count = count + 1
                if count == 5:
                    break
            else:
                break
        d = -d
        p = point
        while True:
            p = p + d
            if self.board[p] == color:
                count = count + 1
                if count == 5:
                    break
            else:
                break
        assert count <= 5
        return count == 5
    
    def point_check_game_end_gomoku(self, point):
        """
            Check if the point causes the game end for the game of Gomoko.
            """
        # check horizontal
        if self._point_direction_check_connect_gomoko(point, 1):
            return True
        
        # check vertical
        if self._point_direction_check_connect_gomoko(point, self.NS):
            return True
        
        # check y=x
        if self._point_direction_check_connect_gomoko(point, self.NS + 1):
            return True
        
        # check y=-x
        if self._point_direction_check_connect_gomoko(point, self.NS - 1):
            return True
        
        return False
    
    def check_game_end_gomoku(self):
        """
            Check if the game ends for the game of Gomoku.
            """
        white_points = where1d(self.board == WHITE)
        black_points = where1d(self.board == BLACK)
        
        for point in white_points:
            if self.point_check_game_end_gomoku(point):
                return True, WHITE
    
        for point in black_points:
            if self.point_check_game_end_gomoku(point):
                return True, BLACK

        return False, None


    ##Assignment 3 starts here
    def find_all_neighbors(self,point):

        return self._neighbors(point)+self._diag_neighbors(point)
        
    def endOfGame(self):

        end,player = self.check_game_end_gomoku()
        return end

    def legalMoves(self):

        return GoBoardUtil.generate_legal_moves_gomoku(self)

    def moveNumber(self):

        return len(self.moves)


    def resetToMoveNumber(self,moveNr):

        numUndos = self.moveNumber() - moveNr
        assert numUndos >= 0
        for _ in range(numUndos):
            self.undoMove()
        assert self.moveNumber() == moveNr

    def undoMove(self):
        location = self.moves.pop()
        self.last_move = location
        self.board[location] = EMPTY
        self.current_player = GoBoardUtil.opponent(self.current_player)

    def simulate(self):
        i = 0
        if not self.endOfGame():
            allMoves = self.legalMoves()
            random.shuffle(allMoves)
            while not self.endOfGame() and i < len(allMoves):
                self.play_move_gomoku(allMoves[i],self.current_player)
                i += 1
        win,winner = self.check_game_end_gomoku()
        if win:
            return winner,i
        return EMPTY, i

    def count(self,point,otherpoint,step):

        if self.get_color(point) != self.get_color(otherpoint):
            return 0
        else:
            return 1 + self.count(point,otherpoint+step,step)

    def five_in_row(self,point,color,step):

        self.board[point] = color
        total = self.count(point,point+step,step) + self.count(point,point-step,-step)
        self.board[point] = EMPTY
        
        return True if total >= 4 else False


    def check_empty(self,point,otherpoint,step):
        if self.get_color(point) != self.get_color(otherpoint):
            return otherpoint
        else:
            return self.check_empty(point,otherpoint+step,step)

    def OpenFour(self,point,color,step):

        if self.OpenFourA(point,color,step):
            return True
        if self.OpenFourB(point,color,step) or self.OpenFourB(point,color,-step):
            return True
        if self.OpenFourC(point,color,step) or self.OpenFourC(point,color,-step):
            return True
        return False

    def OpenFourA(self,point,color,step):

        self.board[point] = color
        total = self.count(point,point+step,step) + self.count(point,point-step,-step)
        if total == 3:
            emptyA=self.check_empty(point,point+step,step)
            emptyB=self.check_empty(point,point-step,-step)
            self.board[point] = EMPTY
            if self.get_color(emptyA) == self.get_color(emptyB) == EMPTY:
                return True
        self.board[point] = EMPTY
        return False

    def BlockOpenFourA(self,point,color,step):

        self.board[point] = color
        total = self.count(point,point+step,step) + self.count(point,point-step,-step)
        if total == 3:
            emptyA=self.check_empty(point,point+step,step)
            emptyB=self.check_empty(point,point-step,-step)
            self.board[point] = EMPTY
            if self.get_color(emptyA) == self.get_color(emptyB) == EMPTY:
                self.board[point] = EMPTY
                return True

        if self.get_color(point-step) != EMPTY and (self.get_color(point+step) == self.get_color(point+2*step) == self.get_color(point+3*step) == color) and \
            (self.get_color(point+4*step) == self.get_color(point+5*step) == EMPTY):
            self.board[point] = EMPTY
            return True
        if self.get_color(point+step) != EMPTY and (self.get_color(point-step) == self.get_color(point-2*step) == self.get_color(point-3*step) == color) and \
            (self.get_color(point-4*step) == self.get_color(point-5*step) == EMPTY):
            self.board[point] = EMPTY
            return True

        self.board[point] = EMPTY
        return False

    def OpenFourB(self,point,color,step):

        if self.get_color(point+step) == color and self.get_color(point+2*step) == color and \
            self.get_color(point+3*step) == EMPTY and self.get_color(point+4*step) == color and \
            self.get_color(point+5*step) == EMPTY:
            return True

    def OpenFourC(self,point,color,step):

        if self.get_color(point-step) == color and self.get_color(point-2*step) == EMPTY and \
            self.get_color(point-3*step) == color and self.get_color(point-4*step) == color and \
            self.get_color(point-5*step) == EMPTY:
            return True

    def BlockOpenFour(self,point,color,step):
        
        left = point+step
        right = point-step
        if self.get_color(left) == EMPTY:
            if self.BlockOpenFourA(left,color,step) and self.get_color(left+5*step) != EMPTY:
                return True

        if self.get_color(right) == EMPTY:
            if self.BlockOpenFourA(right,color,step) and self.get_color(right-5*step) != EMPTY:
                return True

        if self.BlockOpenFourA(point,color,step):
            return True

        if self.OpenFourB(point,color,step) or self.OpenFourB(point,color,-step):
            return True

        if self.OpenFourC(point,color,step) or self.OpenFourC(point,color,-step):
            return True

        return False

    #.OOO.
    def OpenThree(self,point,color,step):

        if self.get_color(point-step) == self.get_color(point+3*step) == EMPTY and self.get_color(point+step) == self.get_color(point+2*step) == color:
            return True
        if self.get_color(point+step) == self.get_color(point-3*step) == EMPTY and self.get_color(point-step) == self.get_color(point-2*step) == color:
            return True

        if self.get_color(point+step) == self.get_color(point-3*step) == EMPTY and self.get_color(point-step) == self.get_color(point-2*step) == color:
            return True
        if self.get_color(point-step) == self.get_color(point+3*step) == EMPTY and self.get_color(point+step) == self.get_color(point+2*step) == color:
            return True

        if self.get_color(point-2*step) == self.get_color(point+2*step) == EMPTY and self.get_color(point-step) == self.get_color(point+step) == color:
            return True

        if self.get_color(point+2*step) == self.get_color(point-2*step) == EMPTY and self.get_color(point+step) == self.get_color(point-step) == color:
            return True

        return False

    #.OO.
    def OpenTwo(self,point,color,step):
        if self.get_color(point-step) == self.get_color(point+2*step) == EMPTY and self.get_color(point+step) == color:
            return True
        if self.get_color(point+step) == self.get_color(point-2*step) == EMPTY and self.get_color(point-step) == color:
            return True

        return False






