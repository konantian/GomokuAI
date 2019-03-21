#!/usr/bin/python3
#/usr/local/bin/python3
# Set the path to your python3 above

from gtp_connection import GtpConnection,move_to_coord,coord_to_point
from board_util import GoBoardUtil,EMPTY, BLACK, WHITE
from simple_board import SimpleGoBoard
import numpy as np

class SimulationPlayer(object):
    def __init__(self, numSimulations):
        self.numSimulations = numSimulations
        self.name = "GomokuAssignment3"
        self.version = 1.0

    def name(self):
        return "Simulation Player ({0} sim.)".format(self.numSimulations)

    def genmove(self, moves,state,color):
        assert not state.endOfGame()
        numMoves = len(moves)
        score = [0] * numMoves
        for i in range(numMoves):
            move = moves[i]
            score[i] = self.simulate(state, move, color)
        bestIndex = np.argmax(score)
        scores=dict(zip(moves,score))
        best = moves[bestIndex]
        return best

    def simulate(self, state, move, color):
        stats = [0] * 3
        #convert the last move to the index point
        coord = move_to_coord(move,state.size)
        point = coord_to_point(coord[0],coord[1],state.size)
        state.play_move_gomoku(point,color)
        moveNr = state.moveNumber()
        for _ in range(self.numSimulations):
            winner, _ = state.simulate()
            stats[winner] += 1
            state.resetToMoveNumber(moveNr)
        assert sum(stats) == self.numSimulations
        assert moveNr == state.moveNumber()
        state.undoMove()
        eval = (stats[BLACK] + 0.5 * stats[EMPTY]) / self.numSimulations
        if state.current_player == WHITE:
            eval = 1 - eval
        return eval
    
def run():
    """
    start the gtp connection and wait for commands.
    """
    board = SimpleGoBoard(10)
    con = GtpConnection(SimulationPlayer(50), board)
    con.start_connection()

if __name__=='__main__':
    run()
