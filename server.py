import json
import socket
import threading
from typing import Optional

HOST = "127.0.0.1"
PORT = 5050

# UPDATED: Increased to 7x7 based on Tanvir's request
BOARD_SIZE = 7
# UPDATED: Added a size 4 ship for the larger board
SHIP_LENGTHS = [4, 3, 2]

matchmaking_queue = []
queue_lock = threading.Lock()

def make_board():
    return [["~" for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

def copy_board(board):
    return [row[:] for row in board]

def hidden_enemy_board(board):
    hidden = make_board()
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col] == "X":
                hidden[row][col] = "X"
            elif board[row][col] == "O":
                hidden[row][col] = "O"
    return hidden

def in_bounds(row, col):
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

def get_ship_cells(row, col, direction, length):
    cells = []
    if direction == "H":
        for i in range(length):
            cells.append((row, col + i))
    elif direction == "V":
        for i in range(length):
            cells.append((row + i, col))
    return cells

def can_place_ship(board, row, col, direction, length):
    if direction not in ("H", "V"):
        return False
    cells = get_ship_cells(row, col, direction, length)
    if len(cells) != length:
        return False
    for r, c in cells:
        if not in_bounds(r, c):
            return False
        if board[r][c] != "~":
            return False
    return True

def place_ship(board, row, col, direction, length):
    for r, c in get_ship_cells(row, col, direction, length):
        board[r][c] = "S"

def all_ships_sunk(board):
    for row in board:
        if "S" in row:
            return False
    return True

class PlayerConnection:
    def __init__(self, conn: socket.socket, addr):
        self.conn = conn
        self.addr = addr
        self.file = conn.makefile("r")
        self.name = "Player"
        self.connected = True

    def send_json(self, payload) -> bool:
        try:
            message = json.dumps(payload) + "\n"
            self.conn.sendall(message.encode("utf-8"))
            return True
        except Exception:
            self.connected = False
            return False

    def recv_json(self) -> Optional[dict]:
        try:
            line = self.file.readline()
            if not line:
                self.connected = False
                return None
            return json.loads(line)
        except Exception:
            self.connected = False
            return None

    def close(self):
        self.connected = False
        try:
            self.file.close()
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass

class GameSession:
    def __init__(self, player1: PlayerConnection, player2: PlayerConnection):
        self.player1 = player1
        self.player2 = player2
        self.board1 = make_board()
        self.board2 = make_board()
        self.turn = 0

    def send_state(self, player, your_board, enemy_board, phase, your_turn, message, place_length=None):
        return player.send_json(
            {
                "type": "STATE",
                "phase": phase,
                "your_board": copy_board(your_board),
                "enemy_board": copy_board(enemy_board),
                "your_turn": your_turn,
                "message": message,
                "place_length": place_length,
                "board_size": BOARD_SIZE,
            }
        )

    def receive_name(self, player: PlayerConnection, fallback_name: str) -> Optional[str]:
        if not player.send_json({"type": "PROMPT_NAME", "message": "Enter your name"}):
            return None
        msg = player.recv_json()
        if msg is None:
            return None
        if msg.get("type") != "NAME":
            player.send_json({"type": "ERROR", "message": "Expected NAME message."})
            return fallback_name
        raw_name = str(msg.get("name", "")).strip()
        if not raw_name:
            return fallback_name
        return raw_name[:20]

    def handle_ship_placement(self, player, my_board, enemy_board):
        for ship_length in SHIP_LENGTHS:
            while True:
                ok = self.send_state(
                    player=player,
                    your_board=my_board,
                    enemy_board=hidden_enemy_board(enemy_board),
                    phase="placement",
                    your_turn=False,
                    message=f"{player.name}: place ship of length {ship_length}",
                    place_length=ship_length,
                )
                if not ok:
                    return False
                msg = player.recv_json()
                if msg is None:
                    return False
                if msg.get("type") != "PLACE_SHIP":
                    player.send_json({"type": "ERROR", "message": "Expected PLACE_SHIP message."})
                    continue
                try:
                    row = int(msg.get("row"))
                    col = int(msg.get("col"))
                    direction = str(msg.get("direction", "")).upper()
                    length = int(msg.get("length"))
                except Exception:
                    player.send_json({"type": "ERROR", "message": "Invalid placement data."})
                    continue
                if length != ship_length:
                    player.send_json({"type": "ERROR", "message": "Incorrect ship length."})
                    continue
                if not in_bounds(row, col):
                    player.send_json({"type": "ERROR", "message": "Placement start out of bounds."})
                    continue
                if not can_place_ship(my_board, row, col, direction, length):
                    player.send_json({"type": "ERROR", "message": "Cannot place ship there."})
                    continue
                place_ship(my_board, row, col, direction, length)
                break
        return True

    def handle_turn(self, active_player, active_board, other_player, other_board):
        while True:
            ok_active = self.send_state(
                player=active_player,
                your_board=active_board,
                enemy_board=hidden_enemy_board(other_board),
                phase="battle",
                your_turn=True,
                message=f"Your turn, {active_player.name}. Click the enemy board to fire.",
            )
            ok_other = self.send_state(
                player=other_player,
                your_board=other_board,
                enemy_board=hidden_enemy_board(active_board),
                phase="battle",
                your_turn=False,
                message=f"Waiting for {active_player.name} to fire...",
            )
            if not ok_active or not ok_other:
                return False
            msg = active_player.recv_json()
            if msg is None:
                return False
            if msg.get("type") != "FIRE":
                active_player.send_json({"type": "ERROR", "message": "Expected FIRE message."})
                continue
            try:
                row = int(msg.get("row"))
                col = int(msg.get("col"))
            except Exception:
                active_player.send_json({"type": "ERROR", "message": "Invalid shot coordinates."})
                continue
            if not in_bounds(row, col):
                active_player.send_json({"type": "ERROR", "message": "Shot out of bounds."})
                continue
            target = other_board[row][col]
            if target in ("X", "O"):
                active_player.send_json({"type": "ERROR", "message": "You already fired there."})
                continue
            if target == "S":
                other_board[row][col] = "X"
                result_message = f"{active_player.name} fired at ({row}, {col}) and hit!"
            else:
                other_board[row][col] = "O"
                result_message = f"{active_player.name} fired at ({row}, {col}) and missed."
            active_player.send_json({"type": "INFO", "message": result_message})
            other_player.send_json({"type": "INFO", "message": result_message})
            return True

    def run(self):
        try:
            self.player1.send_json({"type": "WELCOME", "payload": "Player 1"})
            self.player2.send_json({"type": "WELCOME", "payload": "Player 2"})

            name1 = self.receive_name(self.player1, "Player 1")
            if name1 is None:
                self.player2.send_json({"type": "GAME_OVER", "message": "Other player disconnected."})
                return
            self.player1.name = name1

            name2 = self.receive_name(self.player2, "Player 2")
            if name2 is None:
                self.player1.send_json({"type": "GAME_OVER", "message": "Other player disconnected."})
                return
            self.player2.name = name2

            if not self.handle_ship_placement(self.player1, self.board1, self.board2):
                self.player2.send_json({"type": "GAME_OVER", "message": f"{self.player1.name} disconnected."})
                return
            if not self.handle_ship_placement(self.player2, self.board2, self.board1):
                self.player1.send_json({"type": "GAME_OVER", "message": f"{self.player2.name} disconnected."})
                return

            self.player1.send_json({"type": "INFO", "message": "Battle begins."})
            self.player2.send_json({"type": "INFO", "message": "Battle begins."})

            while True:
                if self.turn == 0:
                    ok = self.handle_turn(self.player1, self.board1, self.player2, self.board2)
                    if not ok:
                        self.player2.send_json({"type": "GAME_OVER", "message": "You win by default."})
                        return
                    if all_ships_sunk(self.board2):
                        self.send_state(self.player1, self.board1, hidden_enemy_board(self.board2), "game_over", False, "You win!")
                        self.send_state(self.player2, self.board2, hidden_enemy_board(self.board1), "game_over", False, "You lose.")
                        self.player1.send_json({"type": "GAME_OVER", "message": "You win!"})
                        self.player2.send_json({"type": "GAME_OVER", "message": "You lose."})
                        return
                    self.turn = 1
                else:
                    ok = self.handle_turn(self.player2, self.board2, self.player1, self.board1)
                    if not ok:
                        self.player1.send_json({"type": "GAME_OVER", "message": "You win by default."})
                        return
                    if all_ships_sunk(self.board1):
                        self.send_state(self.player2, self.board2, hidden_enemy_board(self.board1), "game_over", False, "You win!")
                        self.send_state(self.player1, self.board1, hidden_enemy_board(self.board2), "game_over", False, "You lose.")
                        self.player2.send_json({"type": "GAME_OVER", "message": "You win!"})
                        self.player1.send_json({"type": "GAME_OVER", "message": "You lose."})
                        return
                    self.turn = 0
        finally:
            self.player1.close()
            self.player2.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[STARTING] Battleship server listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            print(f"[CONNECT] Connection from {addr}")
            temp_player = PlayerConnection(conn, addr)
            first_msg = temp_player.recv_json()

            if first_msg is None or first_msg.get("type") != "CONNECT":
                temp_player.close()
                continue

            with queue_lock:
                matchmaking_queue.append(temp_player)
                print(f"[QUEUE] Player added. Queue size: {len(matchmaking_queue)}")

                if len(matchmaking_queue) >= 2:
                    player1 = matchmaking_queue.pop(0)
                    player2 = matchmaking_queue.pop(0)
                    print("[MATCH] 2 players found. Starting Battleship session.")
                    threading.Thread(target=GameSession(player1, player2).run, daemon=True).start()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server closing...")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()