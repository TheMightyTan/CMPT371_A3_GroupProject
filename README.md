# CMPT 371 A3 Socket Programming Battleship

Course: CMPT 371 - Data Communications & Networking  
Instructor: Mirza Zaeem Baig  
Semester: Spring 2026  

---

## Group Members

Name	Student ID          Email
Tanvir Samra	301-571-825 tss19@sfu.ca
Krish Mann	301-565-069     

---

## 1. Project Overview & Description

This project is a multiplayer Battleship game built using Python's Socket API (TCP). It allows two clients to connect to a central server, be matched into a game session, and play against each other in real-time using a graphical user interface (GUI).

The server is responsible for handling all game logic, including ship placement validation, turn-based attacks, board state updates, and win-condition checking. This ensures that clients cannot cheat by modifying their local game state.

The client is implemented using Tkinter and provides an interactive GUI where players can:
- Connect to the server
- Enter their name
- Place ships visually
- Click on the opponent’s board to attack
- Receive real-time updates from the server

---

## 2. System Limitations & Edge Cases

As required by the project specifications, we have identified and handled (or defined) the following limitations and potential issues within our application scope:

### Handling Multiple Clients Concurrently:
Solution: We utilized Python’s threading module. When two clients connect, they are placed into a matchmaking queue and assigned to a GameSession running on a separate thread. This allows multiple games to run simultaneously without blocking the server.

Limitation: Thread creation is limited by system resources. A more scalable solution would involve using asynchronous I/O (such as asyncio) or a thread pool.

---

### TCP Stream Buffering:
Solution: TCP is a continuous byte stream, meaning multiple JSON messages can arrive combined. We addressed this by appending a newline `\n` to each JSON message and processing incoming data line-by-line.

---

### Input Validation & Security:
Solution: The server validates ship placement and attack coordinates to ensure valid gameplay.

Limitation: The server assumes well-formed JSON messages. A modified or malicious client could attempt to send invalid data.

---

### Fixed Game Configuration:
- Board size is fixed at 7x7  
- Ship lengths are fixed as [4, 3, 2]  
- These values are not configurable at runtime  

---

### Localhost Restriction:
The application runs on 127.0.0.1 (localhost). To allow remote gameplay, the host IP would need to be modified.

---

## 3. Video Demo

Our 2-minute video demonstration covering connection setup, gameplay, and termination can be viewed below:

▶️ Add your video link here

---

## 4. Prerequisites (Fresh Environment)

To run this project, you need:

- Python 3.10 or higher  
- No external pip installations are required  

Libraries used:
- socket  
- threading  
- json  
- tkinter  

(Optional) VS Code or Terminal  

RUBRIC NOTE: No external libraries are required, so a requirements.txt file is not necessary.

---

## 5. Step-by-Step Run Guide


### Step 1: Start the Server

Open your terminal and navigate to the project folder. The server binds to 127.0.0.1 on port 5050.

python server.py  

Console output:  
"[STARTING] Battleship server listening on 127.0.0.1:5050"

---

### Step 2: Connect Player 1

Open a new terminal window (keep the server running).

python client.py  

Actions:
- Click "Connect"
- Enter your name
- Click "Send Name"

GUI output:  
"Connected. Waiting for server."

---

### Step 3: Connect Player 2

Open another terminal window.

python client.py  

Actions:
- Click "Connect"
- Enter your name
- Click "Send Name"

GUI output:  
"Matched! Player 1 / Player 2"

---

### Step 4: Ship Placement

Each player must place ships in the following order:
- Length 4
- Length 3
- Length 2

Instructions:
- Select direction (Horizontal or Vertical)
- Hover over the board to preview placement
- Click to place ships
- Invalid placements will be rejected

---

### Step 5: Gameplay

- Players take turns attacking the opponent’s board
- Click on the enemy board to fire
- The server processes the move and updates both boards

Results:
- Hit → X  
- Miss → O  

---

### Step 6: Game Termination

The game ends when all ships of one player are sunk.

- A message will display:
  - "You win!" or "You lose."
- The connection terminates automatically

---

## 6. Technical Protocol Details (JSON over TCP)

We designed a custom application-layer protocol using JSON over TCP.

### Message Format:
{"type": <string>, ...}

---

### Handshake Phase:
Client sends:  
{"type": "CONNECT"}  

Server responds:  
{"type": "WELCOME", "payload": "Player 1"}  

---

### Name Exchange:
Client sends:  
{"type": "NAME", "name": "X"}  

---

### Ship Placement:
Client sends:  
{"type": "PLACE_SHIP", "row": 1, "col": 2, "direction": "H", "length": 3}  

---

### Gameplay:
Client sends:  
{"type": "FIRE", "row": 3, "col": 4}  

Server broadcasts updates:  
{"type": "STATE", "phase": "battle", "your_turn": true, "your_board": [...], "enemy_board": [...]}  

---

### Game Over:
{"type": "GAME_OVER", "message": "You win!"}  

---

## 7. Academic Integrity & References:

---

Code Origin:
    - The Socket boilerplate was adapted from the reference/tutorial videos in the assignment file.
    - ChatGPT was used to help in the READ.md file in terms of polishing and formating

References:
    -https://youtube.com/playlist?list=PL-8C2cUhmkO1yWLTCiqf4mFXId73phvdx&si=FIq3OxypbBeWHhYm
    -https://www.youtube.com/playlist?list=PLhTjy8cBISErYuLZUvVOYsR1giva2payF