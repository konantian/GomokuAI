"""
gtp_connection.py
Module for playing games of Go using GoTextProtocol

Parts of this code were originally based on the gtp module 
in the Deep-Go project by Isaac Henrion and Amos Storkey 
at the University of Edinburgh.
"""
import traceback
from sys import stdin, stdout, stderr
from board_util import GoBoardUtil, BLACK, WHITE, EMPTY, BORDER, PASS, \
                       MAXSIZE, coord_to_point
import numpy as np
import re
import signal

class GtpConnection():

    def __init__(self, go_engine, board, debug_mode = False):
        """
        Manage a GTP connection for a Go-playing engine

        Parameters
        ----------
        go_engine:
            a program that can reply to a set of GTP commandsbelow
        board: 
            Represents the current board state.
        """
        self._debug_mode = debug_mode
        self.go_engine = go_engine
        self.board = board
        self.policy_type = "rule_based"
        #signal.signal(signal.SIGALRM, self.handler)
        self.commands = {
            "protocol_version": self.protocol_version_cmd,
            "quit": self.quit_cmd,
            "name": self.name_cmd,
            "boardsize": self.boardsize_cmd,
            "showboard": self.showboard_cmd,
            "clear_board": self.clear_board_cmd,
            "komi": self.komi_cmd,
            "version": self.version_cmd,
            "known_command": self.known_command_cmd,
            "genmove": self.genmove_cmd,
            "list_commands": self.list_commands_cmd,
            "play": self.play_cmd,
            "legal_moves": self.legal_moves_cmd,
            "gogui-rules_game_id": self.gogui_rules_game_id_cmd,
            "gogui-rules_board_size": self.gogui_rules_board_size_cmd,
            "gogui-rules_legal_moves": self.gogui_rules_legal_moves_cmd,
            "gogui-rules_side_to_move": self.gogui_rules_side_to_move_cmd,
            "gogui-rules_board": self.gogui_rules_board_cmd,
            "gogui-rules_final_result": self.gogui_rules_final_result_cmd,
            "gogui-analyze_commands": self.gogui_analyze_cmd,
            "timelimit": self.timelimit_cmd,
            "policy_moves": self.policy_moves_cmd,
            "policy": self.policy_cmd,
            "count":self.count_color_cmd
        }
        self.timelimit = 60
        self.open = False
        # used for argument checking
        # values: (required number of arguments, 
        #          error message on argnum failure)
        self.argmap = {
            "boardsize": (1, 'Usage: boardsize INT'),
            "komi": (1, 'Usage: komi FLOAT'),
            "known_command": (1, 'Usage: known_command CMD_NAME'),
            "genmove": (1, 'Usage: genmove {w,b}'),
            "play": (2, 'Usage: play {b,w} MOVE'),
            "legal_moves": (1, 'Usage: legal_moves {w,b}')
        }
        self.all_points = GoBoardUtil.generate_legal_moves_gomoku(self.board)
        moves = self.legalMoves()
        self.move_to_point=dict(zip(moves,self.all_points))
        self.point_to_move=dict(zip(self.all_points,moves))
    
    def write(self, data):
        stdout.write(data) 

    def flush(self):
        stdout.flush()

    def start_connection(self):
        """
        Start a GTP connection. 
        This function continuously monitors standard input for commands.
        """
        line = stdin.readline()
        while line:
            self.get_cmd(line)
            line = stdin.readline()

    def get_cmd(self, command):
        """
        Parse command string and execute it
        """
        if len(command.strip(' \r\t')) == 0:
            return
        if command[0] == '#':
            return
        # Strip leading numbers from regression tests
        if command[0].isdigit():
            command = re.sub("^\d+", "", command).lstrip()

        elements = command.split()
        if not elements:
            return
        command_name = elements[0]; args = elements[1:]
        if self.has_arg_error(command_name, len(args)):
            return
        if command_name in self.commands:
            try:
                self.commands[command_name](args)
            except Exception as e:
                self.debug_msg("Error executing command {}\n".format(str(e)))
                self.debug_msg("Stack Trace:\n{}\n".
                               format(traceback.format_exc()))
                raise e
        else:
            self.debug_msg("Unknown command: {}\n".format(command_name))
            self.error('Unknown command')
            stdout.flush()

    def has_arg_error(self, cmd, argnum):
        """
        Verify the number of arguments of cmd.
        argnum is the number of parsed arguments
        """
        if cmd in self.argmap and self.argmap[cmd][0] != argnum:
            self.error(self.argmap[cmd][1])
            return True
        return False

    def debug_msg(self, msg):
        """ Write msg to the debug stream """
        if self._debug_mode:
            stderr.write(msg)
            stderr.flush()

    def error(self, error_msg):
        """ Send error msg to stdout """
        stdout.write('? {}\n\n'.format(error_msg))
        stdout.flush()

    def respond(self, response=''):
        """ Send response to stdout """
        stdout.write('= {}\n\n'.format(response))
        stdout.flush()

    def reset(self, size):
        """
        Reset the board to empty board of given size
        """
        self.board.reset(size)
        points = GoBoardUtil.generate_legal_moves_gomoku(self.board)
        moves = self.legalMoves()
        self.move_to_point=dict(zip(moves,points))
        self.point_to_move=dict(zip(points,moves))
        self.open = False

    def board2d(self):
        return str(GoBoardUtil.get_twoD_board(self.board))
        
    def protocol_version_cmd(self, args):
        """ Return the GTP protocol version being used (always 2) """
        self.respond('2')

    def quit_cmd(self, args):
        """ Quit game and exit the GTP interface """
        self.respond()
        exit()

    def name_cmd(self, args):
        """ Return the name of the Go engine """
        self.respond(self.go_engine.name)

    def version_cmd(self, args):
        """ Return the version of the  Go engine """
        self.respond(self.go_engine.version)

    def clear_board_cmd(self, args):
        """ clear the board """
        self.reset(self.board.size)
        self.respond()

    def boardsize_cmd(self, args):
        """
        Reset the game with new boardsize args[0]
        """
        self.reset(int(args[0]))
        self.respond()

    def showboard_cmd(self, args):
        self.respond('\n' + self.board2d())

    def komi_cmd(self, args):
        """
        Set the engine's komi to args[0]
        """
        self.go_engine.komi = float(args[0])
        self.respond()

    def known_command_cmd(self, args):
        """
        Check if command args[0] is known to the GTP interface
        """
        if args[0] in self.commands:
            self.respond("true")
        else:
            self.respond("false")

    def list_commands_cmd(self, args):
        """ list all supported GTP commands """
        self.respond(' '.join(list(self.commands.keys())))

    def legal_moves_cmd(self, args):
        """
        List legal moves for color args[0] in {'b','w'}
        """
        board_color = args[0].lower()
        color = color_to_int(board_color)
        moves = GoBoardUtil.generate_legal_moves(self.board, color)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = ' '.join(sorted(gtp_moves))
        self.respond(sorted_moves)

    def play_cmd(self, args):
        """
        play a move args[1] for given color args[0] in {'b','w'}
        """
        try:
            board_color = args[0].lower()
            board_move = args[1]
            if board_color != "b" and board_color !="w":
                self.respond("illegal move: \"{}\" wrong color".format(board_color))
                return
            color = color_to_int(board_color)
            if args[1].lower() == 'pass':
                self.board.play_move(PASS, color)
                self.board.current_player = GoBoardUtil.opponent(color)
                self.respond()
                return
            coord = move_to_coord(args[1], self.board.size)
            if coord:
                move = coord_to_point(coord[0],coord[1], self.board.size)
            else:
                self.error("Error executing move {} converted from {}"
                           .format(move, args[1]))
                return
            if not self.board.play_move_gomoku(move, color):
                self.respond("illegal move: \"{}\" occupied".format(board_move))
                return
            else:
                self.debug_msg("Move: {}\nBoard:\n{}\n".
                                format(board_move, self.board2d()))
            self.respond()
        except Exception as e:
            self.respond('{}'.format(str(e)))

    def gogui_rules_game_id_cmd(self, args):
        self.respond("Gomoku")
    
    def gogui_rules_board_size_cmd(self, args):
        self.respond(str(self.board.size))
    
    def legal_moves_cmd(self, args):
        """
            List legal moves for color args[0] in {'b','w'}
            """
        board_color = args[0].lower()
        color = color_to_int(board_color)
        moves = GoBoardUtil.generate_legal_moves(self.board, color)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = ' '.join(sorted(gtp_moves))
        self.respond(sorted_moves)

    def gogui_rules_legal_moves_cmd(self, args):
        game_end,_ = self.board.check_game_end_gomoku()
        if game_end:
            self.respond()
            return
        moves = GoBoardUtil.generate_legal_moves_gomoku(self.board)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = ' '.join(sorted(gtp_moves))
        self.respond(sorted_moves)
    
    def gogui_rules_side_to_move_cmd(self, args):
        color = "black" if self.board.current_player == BLACK else "white"
        self.respond(color)
    
    def gogui_rules_board_cmd(self, args):
        size = self.board.size
        str = ''
        for row in range(size-1, -1, -1):
            start = self.board.row_start(row + 1)
            for i in range(size):
                point = self.board.board[start + i]
                if point == BLACK:
                    str += 'X'
                elif point == WHITE:
                    str += 'O'
                elif point == EMPTY:
                    str += '.'
                else:
                    assert False
            str += '\n'
        self.respond(str)
    
    def gogui_rules_final_result_cmd(self, args):
        game_end, winner = self.board.check_game_end_gomoku()
        moves = self.board.get_empty_points()
        board_full = (len(moves) == 0)
        if board_full and not game_end:
            self.respond("draw")
            return
        if game_end:
            color = "black" if winner == BLACK else "white"
            self.respond(color)
        else:
            self.respond("unknown")

    def gogui_analyze_cmd(self, args):
        self.respond("pstring/Legal Moves For ToPlay/gogui-rules_legal_moves\n"
                     "pstring/Side to Play/gogui-rules_side_to_move\n"
                     "pstring/Final Result/gogui-rules_final_result\n"
                     "pstring/Board Size/gogui-rules_board_size\n"
                     "pstring/Rules GameID/gogui-rules_game_id\n"
                     "pstring/Show Board/gogui-rules_board\n"
                     )

    #####Assignment 3 starts here##############################
    def legalMoves(self):
        moves = GoBoardUtil.generate_legal_moves_gomoku(self.board)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))

        return gtp_moves

    def policy_cmd(self,args):
        self.policy_type = args[0]
        self.respond("")

    def timelimit_cmd(self, args):
        self.timelimit = int(args[0])
        self.respond('')

    def count_color(self,color):
        count = 0
        empty_points = self.all_points
        for point in empty_points:
            if self.board.get_color(point) == color:
                count += 1

        return count

    def find_stone(self,color):
        
        empty_points = self.all_points
        for point in empty_points:
            if self.board.get_color(point) == color:
                return point

    def check_direction(self,pointA,pointB):

        vert_steps = [1,self.board.NS,-1,-self.board.NS]
        for step in vert_steps:
            if pointA + step == pointB:
                return 'vert_hori',step

        diag_steps = [self.board.NS-1,self.board.NS+1,1-self.board.NS,-self.board.NS-1]
        for step in diag_steps:
            if pointA + step == pointB:
                return 'diagonal',step

        return 'None',None

    def count_color_cmd(self,color):
        color = BLACK if color == 'b' else WHITE
        count = 0
        empty_moves = self.legalMoves()
        empty_points=[self.move_to_point[move] for move in empty_moves]
        self.respond(str(empty_points))
        for point in empty_points:
            if self.board.get_color(point) == color:
                count += 1

        self.respond(str(count))

    def policy_moves(self):

        #Opening
        
        if self.count_color(BLACK) == 0:
            return "First Move, ",["D4"]

        if self.count_color(BLACK) == 1 and self.board.get_color(36) == EMPTY and self.board.current_player == WHITE:
            return "First Move, ",["D4"]


        if self.count_color(self.board.current_player) == 1 and self.count_color(GoBoardUtil.opponent(self.board.current_player)) >= 1:
            my_position = self.find_stone(self.board.current_player)
            #print(black_position,white_position)
            #direction,step = self.check_direction(black_position,white_position)
            #if direction == "vert_hori":
            pointsA = self.board.StraightOpening(my_position)
            #print(pointsA)
            return "Opening ",[self.point_to_move[point] for point in pointsA]
        
        empty_moves = self.legalMoves()
        win_moves=[]
        block_win_moves=[]
        open_four_moves=[]
        block_open_four_moves=[]
        open_three_moves = []
        double_open_three = []
        block_open_three = []
        double_dead_four = []
        block_dead_four = []
        
        steps = [1,self.board.NS,self.board.NS-1,self.board.NS+1]
        for move in empty_moves:
            for step in steps:
                point = self.move_to_point[move]
                if self.board.five_in_row(point,self.board.current_player,step):
                    win_moves.append(move)
                elif self.board.five_in_row(point,GoBoardUtil.opponent(self.board.current_player),step):
                    block_win_moves.append(move)
                elif self.board.OpenFour(point,self.board.current_player,step):
                    open_four_moves.append(move)
                elif self.board.BlockOpenFour(point,GoBoardUtil.opponent(self.board.current_player),step):
                    block_open_four_moves.append(move)
                elif self.board.OpenThree(point,self.board.current_player,step):
                    open_three_moves.append(move)
                elif self.board.OpenThree(point,GoBoardUtil.opponent(self.board.current_player),step):
                    block_open_three.append(move)
                elif self.board.DeadFour(point,self.board.current_player,step):
                    double_dead_four.append(move)
                elif self.board.DeadFour(point,GoBoardUtil.opponent(self.board.current_player),step):
                    block_dead_four.append(move)


        dead_four_open_three = set(double_dead_four).intersection(set(open_three_moves))
        double_open_three = [move for move in set(open_three_moves) if open_three_moves.count(move) > 1]
        block_open_three = [move for move in set(block_open_three) if block_open_three.count(move) > 1]
        double_dead_four = [move for move in set(double_dead_four) if double_dead_four.count(move) > 1]
        block_dead_four = [move for move in set(block_dead_four) if block_dead_four.count(move) > 1]

        #print(double_dead_four)
        move_types=["Win ","BlockWin ","OpenFour ","DoubleDeadFour","BlockOpenFour ","BlockDoubleDeadFour ","DeadFourOpenThree ","DoubleOpenThree","BlockDoubleThree","OpenThree ","Random "]
        moves=[win_moves,block_win_moves,open_four_moves,double_dead_four,block_open_four_moves,block_dead_four,dead_four_open_three,double_open_three,block_open_three,open_three_moves,empty_moves]
        for i in range(len(move_types)):
            if moves[i]:
                return move_types[i],moves[i]

    def policy_moves_cmd(self,args):
        
        move_type,moves = self.policy_moves()
        if moves:
            move_as_string = ' '.join(sorted(moves))
            self.respond(move_type+move_as_string)
        else:
            self.respond(" ")
        return

    def genmove_cmd(self, args):
        """
        Generate a move for the color args[0] in {'b', 'w'}, for the game of gomoku.
        """
        board_color = args[0].lower()
        color = color_to_int(board_color)
        game_end, winner = self.board.check_game_end_gomoku()
        if game_end or len(self.legalMoves()) == 0:
            if winner == color:
                self.respond("pass")
            elif len(self.legalMoves()) == 0:
                self.respond("pass")
            else:
                self.respond("resign")
            return
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(self.timelimit)
        try:
            move_type,pending_moves = self.policy_moves()
            move = self.go_engine.genmove(pending_moves,self.board, color)
            signal.alarm(0)
        except Exception as e:
            move = self.go_engine.bestMove

        if move == PASS:
            self.respond("pass")
            return
        coord = move_to_coord(move,self.board.size)
        point = coord_to_point(coord[0],coord[1],self.board.size)
        if self.board.is_legal_gomoku(point, color):
            self.board.play_move_gomoku(point, color)
            self.respond(move)

def signal_handler(signum, frame):
    raise Exception("Timed out!")
            
def point_to_coord(point, boardsize):
    """
    Transform point given as board array index 
    to (row, col) coordinate representation.
    Special case: PASS is not transformed
    """
    if point == PASS:
        return PASS
    else:
        NS = boardsize + 1
        return divmod(point, NS)

def format_point(move):
    """
    Return move coordinates as a string such as 'a1', or 'pass'.
    """
    column_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    #column_letters = "abcdefghjklmnopqrstuvwxyz"
    if move == PASS:
        return "pass"
    row, col = move
    if not 0 <= row < MAXSIZE or not 0 <= col < MAXSIZE:
        raise ValueError
    return column_letters[col - 1]+ str(row) 
    
def move_to_coord(point_str, board_size):
    """
    Convert a string point_str representing a point, as specified by GTP,
    to a pair of coordinates (row, col) in range 1 .. board_size.
    Raises ValueError if point_str is invalid
    """
    if not 2 <= board_size <= MAXSIZE:
        raise ValueError("board_size out of range")
    s = point_str.lower()
    if s == "pass":
        return PASS
    try:
        col_c = s[0]
        if (not "a" <= col_c <= "z") or col_c == "i":
            raise ValueError
        col = ord(col_c) - ord("a")
        if col_c < "i":
            col += 1
        row = int(s[1:])
        if row < 1:
            raise ValueError
    except (IndexError, ValueError):
        raise ValueError("illegal move: \"{}\" wrong coordinate".format(s))
    if not (col <= board_size and row <= board_size):
        raise ValueError("illegal move: \"{}\" wrong coordinate".format(s))
    return row, col

def color_to_int(c):
    """convert character to the appropriate integer code"""
    color_to_int = {"b": BLACK , "w": WHITE, "e": EMPTY, 
                    "BORDER": BORDER}
    return color_to_int[c] 
