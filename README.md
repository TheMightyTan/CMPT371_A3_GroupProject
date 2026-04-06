# CMPT 371 A3 Socket Programming Battleship

Course: CMPT 371 - Data Communications & Networking
Instructor: Mirza Zaeem Baig
Semester: Spring 2026

---

## Group Members

| Name         | Student ID  | Email           |
| ------------ | ----------- | ----------------|
| Tanvir Samra | 301-571-825 | [tss19@sfu.ca]  |
| Krish Mann   | 301-565-069 |                 |

---

## 1. Project Overview & Description

This project is a multiplayer Battleship game built using Python's Socket API (TCP). It allows two clients to connect to a central server, be matched into a game session, and play against each other in real-time using a graphical user interface (GUI).

The server handles all game logic including ship placement validation, turn-based attacks, board updates, and win-condition checking. This ensures fairness and prevents clients from modifying the game locally.

The client is implemented using Tkinter and allows users to connect, enter their name, place ships visually, and attack the opponent’s board through a GUI.

---

## 2. System Limitations & Edge Cases

Handling Multiple Clients Concurrently:
Solution: The server uses Python’s threading module. Each pair of clients is assigned to a separate game session thread so multiple games can run simultaneously.
Limitation: Threads are limited by system resources. A more scalable approach would use asyncio or a thread pool.

TCP Stream Buffering:
Solution: Since TCP is a byte stream, messages can combine. Each JSON message is terminated with a newline `\n` and processed line-by-line.

Input Validation & Security:
Solution: The server validates ship placements and attack coordinates.
Limitation: The server assumes properly formatted JSON messages. A malicious client could send unexpected data.

Fixed Game Configuration:
Board size is fixed at 7x7 and ship sizes are [4, 3, 2]. These values are not configurable.

Localhost Restriction:
The game runs on 127.0.0.1. To support remote play, the IP must be changed.

---

## 3. Video Demo

▶️ [Watch Project Demo](ADD_YOUR_LINK_HERE)

---

## 4. Prerequisites (Fresh Environment)

To run this project, you need:

* Python 3.10 or higher
* No external pip installations are required

Libraries used: socket, threading, json, tkinter

---

## 5. Step-by-Step Run Guide

Step 1: Start the Server
Open your terminal and navigate to the project folder. The server binds to 127.0.0.1 on port 5050. Run:

```bash
python server.py
```

Console output:

```
[STARTING] Battleship server listening on 127.0.0.1:5050
```

Step 2: Connect Player 1
Open a new terminal window (keep the server running) and run:

```bash
python client.py
```

Then:

* Click "Connect"
* Enter your name
* Click "Send Name"

You should see:

```
Connected. Waiting for server.
```

Step 3: Connect Player 2
Open another terminal window and run:

```bash
python client.py
```

Then:

* Click "Connect"
* Enter your name
* Click "Send Name"

Once both players connect:

```
Matched! Player 1 / Player 2
```

Step 4: Ship Placement
Each player places ships in order: length 4, then 3, then 2.
Select direction (horizontal or vertical), hover to preview, and click to place ships. Invalid placements are rejected.

Step 5: Gameplay
Players take turns clicking on the opponent’s board to attack.
The server processes moves and updates both clients in real time.

Results:

* Hit → X
* Miss → O

Step 6: Game Termination
The game ends when all ships of one player are sunk.
A message will display "You win!" or "You lose."
The connection closes automatically.

---

## 6. Technical Protocol Details (JSON over TCP)

Message Format:

```
{"type": <string>, ...}
```

Handshake Phase:

```
Client sends: {"type": "CONNECT"}
Server responds: {"type": "WELCOME", "payload": "Player 1"}
```

Name Exchange:

```
{"type": "NAME", "name": "X"}
```

Ship Placement:

```
{"type": "PLACE_SHIP", "row": 1, "col": 2, "direction": "H", "length": 3}
```

Gameplay Phase:

```
{"type": "FIRE", "row": 3, "col": 4}
Server responds: {"type": "STATE", "phase": "battle", "your_turn": true}
```

Game Over:

```
{"type": "GAME_OVER", "message": "You win!"}
```

---

## 7. Academic Integrity & References

Code Origin:
The socket structure was adapted from course materials and tutorial videos.
ChatGPT was used to assist with README formatting and polishing.

References:
https://youtube.com/playlist?list=PL-8C2cUhmkO1yWLTCiqf4mFXId73phvdx
https://www.youtube.com/playlist?list=PLhTjy8cBISErYuLZUvVOYsR1giva2payF
