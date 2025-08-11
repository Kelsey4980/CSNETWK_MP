from .Player import Player

# ===== << Functions >> ===== #

class TicTacToeGame:
    """
    Representation of a Tic Tac Toe game.
    Contains methods to manage the game state, display the board,
    make moves, and check for a winner.
    """

    def __init__(self, game_id: str, p1_id: str, p1_symbol: str, p2_id: str):
        p2_symbol = "O" if p1_symbol == "X" else "X"

        p1_name = p1_id.split('@')[0]
        p2_name = p2_id.split('@')[0]

        self.p1 = Player(p1_id, p1_name, p1_symbol)
        self.p2 = Player(p2_id, p2_name, p2_symbol)

        self.game_id = game_id
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        self.turn = 0
        self.current_player = self.p1
        self.end = False
        self.winner = None


    '''
        Displays the current state of the board

        Parameters:
        board (2D Array): The board to be displayed
    '''
    def print_board(self):
        top_border = '╔═══════════════════════╗'
        mid_border = '║═══════════════════════║'
        bot_border = '╚═══════════════════════╝'
        empty_row  = '║       ║       ║       ║'

        print('\n')

        previous_player = self.p1 if self.current_player == self.p2 else self.p2
        print(f'\nTurn {self.turn} - {previous_player.name} ({previous_player.symbol})')

        print(top_border)

        for i in range(3):
            print(empty_row)
            print(f'║   {self.board[i][0]}   ║   {self.board[i][1]}   ║   {self.board[i][2]}   ║')
            print(empty_row)
            if i < 2:
                print(mid_border)

        print(bot_border)


    '''
        Checks if the chosen position has been occupied 
        and marks it with the given symbol if not

        Parameters:
        board (2D Array): The board to be analyzed
        position (int): The position to be marked
        symbol (string): The symbol that the position will be marked with

        Returns:
        bool: True if move was successful, otherwise False
    '''
    def move(self, symbol, position):
        x = position // 3
        y = position % 3

        if self.board[x][y] == ' ':
            self.board[x][y] = symbol
            self.turn += 1

            self.switch_current_player()

            return True
        else:
            print("\nInvalid move! Please enter a position that is not occupied\n")
            return False

    '''
        Checks if the game has ended in a draw

        Returns:
        bool: True if the game is a draw, otherwise False
    '''
    def check_draw(self):
        if not any(' ' in row for row in self.board) and not self.check_win()[0]:
            self.end = True

        return self.end

    '''
        Checks the board for win conditions

        Parameters: 
        board (2D Array): The board to be analyzed

        Returns:
        bool: True if a winner is determined, otherwise False
        tuple: List of numbers that represent the winning line
        string: The symbol of the player who won
    '''
    def check_win(self):
        for i in range(3):

            # Horizontal 
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != ' ':
                winning_line = (i * 3 + 0, i * 3 + 1, i * 3 + 2)
                return True, winning_line, self.board[i][0]
            
            # Vertical
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != ' ':
                winning_line = (i, 3 + i, 6 + i)
                return True, winning_line, self.board[0][i]
            
        # Diagonal Left
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != ' ':
            winning_line = (0, 4, 8)
            return True, winning_line, self.board[0][0]
        
        # Diagonal Right
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != ' ':
            winning_line = (2, 4, 6)
            return True, winning_line, self.board[0][2]
        
        return False, None, None
        
    def get_turn_number(self):
        return self.turn
    
    def get_current_player(self):
        return self.current_player
    
    def get_game_id(self):
        return self.game_id
    
    def get_p1(self):
        return self.p1
    
    def get_p2(self):
        return self.p2

    def switch_current_player(self):
        # Switch current player
        if self.current_player == self.p1:
            self.current_player = self.p2
        else:
            self.current_player = self.p1
    

    # ===== << Game >> ===== #

    '''
    while not end:

        print_board(board)

        # --- Get position input --- #
        print(f'\nTurn {turn} - {current_player.name} ({current_player.symbol})')
        try:
            position = int(input("Enter the position you would like to mark (0 - 8): "))
        except ValueError:
            print("\nInvalid input! Please enter a number from 0 to 8.")
            continue
        
        # --- Checks for valid input --- #
        if not (0 <= position <= 8):
            print("\nInvalid input! Please enter a number from 0 to 8.")
            continue
        else:
            valid_move = move(board, position, current_player.symbol)
        
        if valid_move:

            # --- Checks for a draw --- #
            if not any(' ' in row for row in self.board):
                end = True
                break

            # --- Checks for a winner --- #
            end, winning_line, winner_symbol = check_win(board)
            if end:
                a, b, c = winning_line
                winner = p1 if winner_symbol == p1.symbol else p2
                break

            # --- Continues the game --- #
            current_player = p2 if current_player == p1 else p1
            turn += 1

    print_board(board)

    if winner:
        print(f"\n{winner.name} wins!")
        print(f"Winning Line: {a}, {b}, {c}")
    else:
        print("\nIt's a draw!")
    '''