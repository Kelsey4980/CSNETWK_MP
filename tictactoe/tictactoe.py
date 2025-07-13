from Player import Player

# ===== << Functions >> ===== #

'''
    Displays the current state of the board

    Parameters:
    board (2D Array): The board to be displayed
'''
def print_board(board):
    top_border = '╔═══════════════════════╗'
    mid_border = '║═══════════════════════║'
    bot_border = '╚═══════════════════════╝'
    empty_row  = '║       ║       ║       ║'

    print('\n')

    print(top_border)

    for i in range(3):
        print(empty_row)
        print(f'║   {board[i][0]}   ║   {board[i][1]}   ║   {board[i][2]}   ║')
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
def move(board, position, symbol):
    x = position // 3
    y = position % 3

    if board[x][y] == ' ':
        board[x][y] = symbol
        return True
    else:
        print("\nInvalid move! Please enter a position that is not occupied\n")
        return False

'''
    Checks the board for win conditions

    Parameters: 
    board (2D Array): The board to be analyzed

    Returns:
    bool: True if a winner is determined, otherwise False
    tuple: List of numbers that represent the winning line
    string: The symbol of the player who won
'''
def check_win(board):
    for i in range(3):

        # Horizontal 
        if board[i][0] == board[i][1] == board[i][2] != ' ':
            winning_line = (i * 3 + 0, i * 3 + 1, i * 3 + 2)
            return True, winning_line, board[i][0]
        
        # Vertical
        if board[0][i] == board[1][i] == board[2][i] != ' ':
            winning_line = (i, 3 + i, 6 + i)
            return True, winning_line, board[0][i]
        
    # Diagonal Left
    if board[0][0] == board[1][1] == board[2][2] != ' ':
        winning_line = (0, 4, 8)
        return True, winning_line, board[0][0]
    
    # Diagonal Right
    if board[0][2] == board[1][1] == board[2][0] != ' ':
        winning_line = (2, 4, 6)
        return True, winning_line, board[0][2]
    
    return False, None, None
        

# ===== << Game >> ===== #

# --- Temporary values --- #
p1_name = "Alice"
p1_symbol = "X"

p2_name = "Bob"
p2_symbol = "O" if p1_symbol == "X" else "X"

p1 = Player(p1_name, p1_symbol)
p2 = Player(p2_name, p2_symbol)

board = [[' ' for _ in range(3)] for _ in range(3)]
turn = 1
current_player = p1
end = False
winner = None

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
        if not any(' ' in row for row in board):
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