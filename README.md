# Banking Transaction Visualizer using Directed Graphs

## Overview

The Banking Transaction Visualizer is a mini project developed using Python to simulate concurrent banking operations and visualize transaction dependencies using Directed Graphs.

The project demonstrates how modern banking systems maintain transaction consistency and avoid conflicts during simultaneous ATM, online banking, and fund transfer operations.

This project integrates concepts from:
- Discrete Mathematics
- Database Management Systems
- Operating Systems
- Graph Theory

---

# Features

- Deposit, Withdrawal, and Fund Transfer Simulation
- Multiple Users Accessing Same Account
- Conflict Detection
- Automatic Precedence Graph Generation
- Directed Graph Visualization
- DFS-Based Cycle Detection
- Safe and Unsafe Schedule Verification
- Rollback Recovery Simulation
- Transaction History Tracking
- Live Transaction Execution Visualization
- Quiz Mode for Learning Transaction Safety

---

# Concepts Used

## Directed Graphs
Transactions are represented as nodes and dependencies are represented as edges.

## DFS (Depth First Search)
Used to traverse transaction graphs and detect cycles.

## Cycle Detection
Determines whether a transaction schedule is safe or unsafe.

## Transaction Scheduling
Ensures conflict-free execution of concurrent transactions.

---

# Real-World Applications

- ATM Systems
- Mobile Banking Applications
- Online Payment Gateways
- Financial Transaction Systems
- Database Concurrency Control

---

# Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core Programming |
| Tkinter | GUI Development |
| NetworkX | Graph Generation |
| Matplotlib | Graph Visualization |
| JSON / SQLite | Data Storage |

---

# Project Structure

```bash
Banking-Transaction-Visualizer/
│
├── assets/
├── data/
├── src/
├── requirements.txt
├── README.md
└── LICENSE
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/yourusername/Banking-Transaction-Visualizer.git
```

## Navigate to Project Folder

```bash
cd Banking-Transaction-Visualizer
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Run the Project

```bash
python src/main.py
```

---

# Sample Workflow

1. User performs Deposit/Withdrawal/Transfer
2. System checks transaction conflicts
3. Precedence graph is generated
4. DFS algorithm checks cycles
5. Schedule marked SAFE or UNSAFE
6. Rollback recovery executed if required

---

# Example Transaction Graph

```text
T1 → T2 → T3
```

Safe Schedule

```text
T1 → T2 → T3 → T1
```

Unsafe Schedule (Cycle Detected)

---

# Algorithms Used

## DFS Cycle Detection

Time Complexity:
```text
O(V + E)
```

Where:
- V = Number of Transactions
- E = Dependency Edges

---

# Future Enhancements

- AI-Based Fraud Detection
- Cloud Database Integration
- Multi-Bank Transaction Simulation
- Blockchain Transaction Verification
- Real-Time API Integration

---

# Screenshots

(Yet to add)

---

### Learning Outcomes

This project helps understand:
- Graph Theory Applications
- Concurrency Control
- Conflict Serializability
- Transaction Scheduling
- Real-Time Banking Systems

---

### Author

##### SHREEJA HEBBAR
Computer Science Engineering Student

---

### License

This project is licensed under the MIT License.
