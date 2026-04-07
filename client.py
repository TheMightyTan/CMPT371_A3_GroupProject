import json
import queue
import socket
import threading
import tkinter as tk
from tkinter import messagebox

# NETWORK CONFIGURATION
HOST = "127.0.0.1" #default local testing
PORT = 5050 #port our server listening on 

BOARD_SIZE = 7 #Adjust/change the grid/board size/settings from 7*7 to something unique 
CELL_SIZE = 40
MARGIN = 35

COLOR_WATER = "#b7dfff" #these are the color contents for the UI/Board
COLOR_SHIP = "#7a7a7a"
COLOR_HIT = "#ff5c5c"
COLOR_MISS = "#ffffff"
COLOR_GRID = "#000000"
COLOR_PREVIEW_OK = "#98fb98"
COLOR_PREVIEW_BAD = "#ffb6c1"

def send_json(sock, data):
    """Application-Layer Protocol: Converts a dict into JSON which can be sent over the socket; the newline is so that
    the content can be read line by line; it is basically a delimineter (append a newline character ('\\n'))"""
    message = json.dumps(data) + "\n"
    sock.sendall(message.encode("utf-8"))

def recv_json(file_obj):
    """Each line is read from the socket, parsed as JSON, and returns the line;
    If the connection is either closed or an error occurs, None is returned and dealt with later"""
    try:
        line = file_obj.readline()
        if not line:
            return None
        return json.loads(line)
    except Exception:
        return None

class BattleshipGUI:
    """Sets up the GUI and game state by setting up the networking variables, the board and starts the
    UI and the message processing loop"""
    def __init__(self, root): 
        self.root = root
        self.root.title("Battleship Client")

        # Networking state variables
        """Socket connection"""
        self.sock = None
        self.sock_file = None
        self.running = False
        self.connected = False

        # CMPT371 Concept: Thread Safety. Tkinter crashes if background threads update the ui directly.
        # use a thread safe queue to pass network messages grom background reciver thread to the main ui thread.
        self.msg_queue = queue.Queue() #Important to ensure that the queue is thread-safe

        # Client side <-game state
        """This is for the game state"""
        self.phase = "connect"
        self.your_turn = False
        self.place_length = None
        self.direction = "H"

        # initialize empty 2D arrays for the boards
        """The Boards that each user will see"""
        self.your_board = [["~" for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.enemy_board = [["~" for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.hover_row = None
        self.hover_col = None

        #UI elements 
        self.build_ui()
        self.draw_boards()
        self.root.after(100, self.process_messages) #!Important: this will process server messages; have to have this
        self.root.protocol("WM_DELETE_WINDOW", self.on_close) #This will make sure that the window is closed safely

    def build_ui(self):
        #top bar for networking inputs
        # host, port, connect button
        top = tk.Frame(self.root)
        top.pack(pady=8)
        tk.Label(top, text="Host:").grid(row=0, column=0, padx=4)
        self.host_entry = tk.Entry(top, width=14)
        self.host_entry.insert(0, HOST)
        self.host_entry.grid(row=0, column=1, padx=4)
        tk.Label(top, text="Port:").grid(row=0, column=2, padx=4)
        self.port_entry = tk.Entry(top, width=8)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.grid(row=0, column=3, padx=4)
        self.connect_btn = tk.Button(top, text="Connect", command=self.connect_to_server)
        self.connect_btn.grid(row=0, column=4, padx=4)

        #frame for entering players name
        name_frame = tk.Frame(self.root)
        name_frame.pack(pady=6)
        tk.Label(name_frame, text="Name:").grid(row=0, column=0, padx=4)
        self.name_entry = tk.Entry(name_frame, width=18)
        self.name_entry.grid(row=0, column=1, padx=4)
        self.name_btn = tk.Button(name_frame, text="Send Name", state="disabled", command=self.send_name)
        self.name_btn.grid(row=0, column=2, padx=4)

        # ship placement control -> horizontal/vertical
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=6)
        tk.Label(control_frame, text="Direction:").grid(row=0, column=0, padx=4)
        self.direction_var = tk.StringVar(value="H")
        tk.Radiobutton(control_frame, text="Horizontal", variable=self.direction_var, value="H", command=self.update_direction).grid(row=0, column=1, padx=4)
        tk.Radiobutton(control_frame, text="Vertical", variable=self.direction_var, value="V", command=self.update_direction).grid(row=0, column=2, padx=4)

        # frame for actual game grids
        boards_frame = tk.Frame(self.root)
        boards_frame.pack(pady=10)
        left_frame = tk.Frame(boards_frame)
        left_frame.grid(row=0, column=0, padx=18)
        right_frame = tk.Frame(boards_frame)
        right_frame.grid(row=0, column=1, padx=18)
        tk.Label(left_frame, text="Your Board").pack()
        tk.Label(right_frame, text="Enemy Board").pack()

        canvas_width = MARGIN + (BOARD_SIZE * CELL_SIZE) + 20
        canvas_height = MARGIN + (BOARD_SIZE * CELL_SIZE) + 20

        # bind mouse events to the canvas so we can place ships and also fire at them 
        self.your_canvas = tk.Canvas(left_frame, width=canvas_width, height=canvas_height, bg="white")
        self.your_canvas.pack()
        self.enemy_canvas = tk.Canvas(right_frame, width=canvas_width, height=canvas_height, bg="white")
        self.enemy_canvas.pack()

        #status bar at bottom to talk to player
        self.your_canvas.bind("<Button-1>", self.on_your_board_click)
        self.your_canvas.bind("<Motion>", self.on_your_board_hover)
        self.your_canvas.bind("<Leave>", self.on_your_board_leave)
        self.enemy_canvas.bind("<Button-1>", self.on_enemy_board_click)

        self.status_label = tk.Label(self.root, text="Not connected", width=75, anchor="w")
        self.status_label.pack(pady=8)

    def update_direction(self):
        self.direction = self.direction_var.get()
        self.draw_boards()

    def connect_to_server(self):
        """
        Initialize IPv4 TCP socket (AF_INET, SOCK_STREAM) -> then attempts 3 way handshake with server.
        """
        if self.connected: return
        host = self.host_entry.get().strip() or HOST
        try: port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Port must be numeric.")
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.sock_file = self.sock.makefile("r")
            #initial hand shake payload
            send_json(self.sock, {"type": "CONNECT"})
            self.running = True
            self.connected = True
            self.connect_btn.config(state="disabled")
            #concept from CMPT371 : concurrency. we spawn a daemon thread to constantly listen for incoming packets ->to prevent main UI thread to freeze.
            threading.Thread(target=self.receiver_loop, daemon=True).start()
            self.set_status("Connected. Waiting for server.")
        except Exception as exc:
            self.connected = False
            messagebox.showerror("Connection Error", str(exc))

    def receiver_loop(self):
        """
        Runs continuously in the background thread and then pushes incoming packets to thread-safe queue.
        """
        while self.running:
            msg = recv_json(self.sock_file)
            if msg is None:
                self.msg_queue.put({"type": "_DISCONNECT"})
                break
            self.msg_queue.put(msg)

    def process_messages(self):
        """
        Runs on the main UI thread -> then empties the queue and updates the GUI.
        """
        while not self.msg_queue.empty():
            msg = self.msg_queue.get()
            self.handle_message(msg)
        self.root.after(100, self.process_messages)

    def handle_message(self, msg):
        """
        Our custom Application-Layer router. It acts based on the 'type' field in the JSON.
        """
        msg_type = msg.get("type")
        if msg_type == "WELCOME":
            self.set_status(f"Matched! {msg.get('payload', '')}")
        elif msg_type == "PROMPT_NAME":
            self.name_btn.config(state="normal")
            self.set_status(msg.get("message", "Enter your name"))
        elif msg_type == "INFO":
            self.set_status(msg.get("message", ""))
        elif msg_type == "ERROR":
            self.set_status(msg.get("message", "Error"))
        elif msg_type == "STATE":
            self.phase = msg.get("phase", self.phase)
            self.your_turn = bool(msg.get("your_turn", False))
            self.place_length = msg.get("place_length", None)
            self.your_board = msg.get("your_board", self.your_board)
            self.enemy_board = msg.get("enemy_board", self.enemy_board)
            self.set_status(msg.get("message", ""))
            self.draw_boards()
        elif msg_type == "GAME_OVER":
            self.phase = "game_over"
            self.your_turn = False
            self.set_status(msg.get("message", "Game over"))
            self.draw_boards()
            messagebox.showinfo("Game Over", msg.get("message", "Game over"))
        elif msg_type == "_DISCONNECT":
            self.running = False
            self.connected = False
            self.phase = "disconnected"
            self.your_turn = False
            self.set_status("Disconnected from server.")
            self.draw_boards()

    def send_name(self):
        if not self.connected or self.sock is None: return
        name = self.name_entry.get().strip()
        if not name: return
        try:
            send_json(self.sock, {"type": "NAME", "name": name})
            self.name_btn.config(state="disabled")
            self.set_status("Name sent.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def pixel_to_cell(self, x, y):
        """Helper math to figure out which grid cell the user clicked on"""
        if x < MARGIN or y < MARGIN: return None
        col = (x - MARGIN) // CELL_SIZE
        row = (y - MARGIN) // CELL_SIZE
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE: return row, col
        return None

    def get_ship_cells(self, row, col, direction, length):
        """Calculates where the rest of the ship sits/place in reference to starting cell."""
        cells = []
        if direction == "H":
            for i in range(length): cells.append((row, col + i))
        elif direction == "V":
            for i in range(length): cells.append((row + i, col))
        return cells

    def can_place_local(self, row, col, direction, length):
        #client side validation to prevent sending obviously bad data to server.
        cells = self.get_ship_cells(row, col, direction, length)
        if len(cells) != length: return False
        for r, c in cells:
            if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE): return False
            if self.your_board[r][c] != "~": return False
        return True

    def on_your_board_hover(self, event):
        #show the green & red preview shadow when placing a ship.
        if self.phase != "placement" or self.place_length is None:
            self.hover_row, self.hover_col = None, None
            self.draw_boards()
            return
        cell = self.pixel_to_cell(event.x, event.y)
        if cell is None:
            self.hover_row, self.hover_col = None, None
            self.draw_boards()
            return
        row, col = cell
        if row != self.hover_row or col != self.hover_col:
            self.hover_row, self.hover_col = row, col
            self.draw_boards()

    def on_your_board_leave(self, _event):
        self.hover_row, self.hover_col = None, None
        self.draw_boards()

    def on_your_board_click(self, event):
        """Triggered when user clicks their board to place a ship."""
        if self.phase != "placement" or self.place_length is None or not self.connected: return
        cell = self.pixel_to_cell(event.x, event.y)
        if cell is None: return
        row, col = cell
        if not self.can_place_local(row, col, self.direction, self.place_length):
            self.set_status("Invalid placement. Try another cell.")
            return
        try:
            send_json(self.sock, {"type": "PLACE_SHIP", "row": row, "col": col, "direction": self.direction, "length": self.place_length})
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def on_enemy_board_click(self, event):
        """Triggered when user clicks enemy board to launch attack."""
        if self.phase != "battle" or not self.your_turn or not self.connected: return
        cell = self.pixel_to_cell(event.x, event.y)
        if cell is None: return
        row, col = cell
        if self.enemy_board[row][col] in ("X", "O"):
            self.set_status("You already fired there.")
            return
        try:
            send_json(self.sock, {"type": "FIRE", "row": row, "col": col})
            self.your_turn = False
            self.set_status("Shot sent. Waiting for result.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def draw_boards(self):
        """This function will make sure to re-draw both boards for player and opponet"""
        self.draw_single_board(self.your_canvas, self.your_board, reveal_ships=True, preview=True)
        self.draw_single_board(self.enemy_canvas, self.enemy_board, reveal_ships=False, preview=False)

    def draw_single_board(self, canvas, board, reveal_ships, preview):
        # clear canvas to prevent memory leaks like inifintely drawing overlapping rectangles
        canvas.delete("all")
        # Draw coordinate labels (0,1, 2, 3, ..)
        for i in range(BOARD_SIZE):
            x = MARGIN + i * CELL_SIZE + CELL_SIZE // 2
            y = MARGIN + i * CELL_SIZE + CELL_SIZE // 2
            canvas.create_text(x, MARGIN // 2, text=str(i))
            canvas.create_text(MARGIN // 2, y, text=str(i))

        # Loop through 2D array -> then draw grid
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x1 = MARGIN + col * CELL_SIZE
                y1 = MARGIN + row * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                value = board[row][col]

                # state of color from server
                if value == "~": fill = COLOR_WATER
                elif value == "S": fill = COLOR_SHIP if reveal_ships else COLOR_WATER
                elif value == "X": fill = COLOR_HIT
                elif value == "O": fill = COLOR_MISS
                else: fill = COLOR_WATER

                canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=COLOR_GRID)

                # Draw the X (Hit), O (Miss), or S (Ship) characters
                if value == "X": canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text="X", font=("Arial", 16, "bold"))
                elif value == "O": canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text="•", font=("Arial", 16, "bold"))
                elif value == "S" and reveal_ships: canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text="S", font=("Arial", 12, "bold"))

        # draw transparent green/red shadow when placing ships
        if preview and self.phase == "placement" and self.place_length is not None:
            if self.hover_row is not None and self.hover_col is not None:
                cells = self.get_ship_cells(self.hover_row, self.hover_col, self.direction, self.place_length)
                valid = self.can_place_local(self.hover_row, self.hover_col, self.direction, self.place_length)
                preview_color = COLOR_PREVIEW_OK if valid else COLOR_PREVIEW_BAD
                for r, c in cells:
                    if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                        x1 = MARGIN + c * CELL_SIZE
                        y1 = MARGIN + r * CELL_SIZE
                        canvas.create_rectangle(x1, y1, x1 + CELL_SIZE, y1 + CELL_SIZE, fill=preview_color, outline=COLOR_GRID, stipple="gray25")
        #black margin around board
        total = MARGIN + (BOARD_SIZE * CELL_SIZE)
        canvas.create_rectangle(MARGIN, MARGIN, total, total, outline=COLOR_GRID, width=2)

    def set_status(self, text):
        self.status_label.config(text=text)

    def on_close(self):
        """This will close the client connection and safely close the GUI"""
        self.running = False
        self.connected = False
        try:
            if self.sock_file is not None: self.sock_file.close()
            if self.sock is not None: self.sock.close()
        except Exception: pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    BattleshipGUI(root)
    root.mainloop()