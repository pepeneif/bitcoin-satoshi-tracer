# Bitcoin Satoshi Tracer

Trace a satoshi from a given UTXO back to the block it was mined, streaming the history in real-time to an interactive web UI.

## Requirements
- Docker & docker-compose
- Access to a synced Bitcoin Core node with RPC enabled

## Setup
1. Clone the repo
2. Create `.env` with your Bitcoin Core RPC credentials
3. Run:
```
sudo docker-compose up --build
```
4. Open `http://localhost:3000`

## Notes
- This is a prototype; coinjoin handling and address heuristics can be improved.