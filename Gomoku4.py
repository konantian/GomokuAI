#!/usr/bin/python3
#/usr/local/bin/python3
# Set the path to your python3 above

from gtp_connection import GtpConnection,move_to_coord,coord_to_point
from board_util import GoBoardUtil,EMPTY, BLACK, WHITE
from simple_board import SimpleGoBoard
import numpy as np
import copy

class SimulationPlayer(object):
    def __init__(self):
        self.numSimulations = None
        self.name = "GomokuAssignment4"
        self.version = 2.0
        self.preAction = None
        self.moves = None
        self.avg_rewards = None
        self.count = None
        self.c = 2
        self.time = 1
        self.bestMove = None

    def name(self):
        return "Simulation Player ({0} sim.)".format(self.numSimulations)

    def genmove(self,moves,state,color):
        assert not state.endOfGame()
        moveNr = len(moves)
        self.numSimulations = moveNr*100
        if moveNr == 1:
            return moves[0]

        #agent init
        self.moves = moves
        self.count = dict(zip(moves,[0]*moveNr))
        self.avg_rewards = dict(zip(moves,[0]*moveNr))

        #agent start
        self.preAction = self._choose_action()
        self.count[self.preAction] +=1
        self.time += 1
        coord = move_to_coord(self.preAction,state.size)
        point = coord_to_point(coord[0],coord[1],state.size)
        copy_board = copy.deepcopy(state)
        copy_board.play_move_gomoku(point,color)
        reward = copy_board.mysimulate(color)
        self.avg_rewards[self.preAction]+=((reward-self.avg_rewards[self.preAction])/self.count[self.preAction])
        

        highest_reward = max(self.avg_rewards.values())
        for move in self.avg_rewards:
            if self.avg_rewards[move] == highest_reward:
                self.bestMove = move

        #agent step
        while 1:
            self.preAction = self._choose_action()
            self.count[self.preAction] +=1
            self.time += 1
            coord = move_to_coord(self.preAction,state.size)
            point = coord_to_point(coord[0],coord[1],state.size)
            copy_board = copy.deepcopy(state)
            copy_board.play_move_gomoku(point,color)
            reward = copy_board.mysimulate(color)
            self.avg_rewards[self.preAction]+=((reward-self.avg_rewards[self.preAction])/self.count[self.preAction])
            #update self.bestMove
            if self.avg_rewards[self.preAction] > self.avg_rewards[self.bestMove]:
                self.bestMove = self.preAction

        return self.bestMove

    def _choose_action(self):
        if 0 not in self.count.values():
            temp = dict(zip(self.moves,[self.avg_rewards[i]+np.sqrt(np.log(self.time)/self.count[i])*self.c for i in self.moves]))
            greedy_actions = [x for x in temp if temp[x] == max(temp.values())]
        else:
            greedy_actions = [i for i in self.moves if self.count[i] == 0]

        return greedy_actions[np.random.randint(0,len(greedy_actions))]

    def mygenmove(self, moves,state,color):
        assert not state.endOfGame()
        numMoves = len(moves)
        score = [0] * numMoves
        for i in range(numMoves):
            move = moves[i]
            score[i] = self.simulate(state, move, color)
        bestIndex = score.index(max(score))
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
    board = SimpleGoBoard(7)
    con = GtpConnection(SimulationPlayer(), board)
    con.start_connection()

if __name__=='__main__':
    run()
