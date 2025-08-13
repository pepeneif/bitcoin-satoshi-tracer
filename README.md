# Bitcoin Satoshi Tracer

Trace a satoshi from a given UTXO back to the block it was mined, streaming the history in real-time to an interactive web UI.

## Requirements
- Docker & docker-compose
- Access to an Electrs server (e.g., running on an Umbrel node)

## Setup
1. Clone the repo
2. Create `.env` with your Electrs server configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your Electrs server details
   ```
3. Run:
   ```bash
   sudo docker-compose up --build
   ```
4. Open `http://localhost:3000`

## Configuration

The application connects to an Electrs server instead of Bitcoin Core directly. Configure the following environment variables in your `.env` file:

- `ELECTRS_HOST`: Your Electrs server hostname or IP address
- `ELECTRS_PORT`: Electrs TCP port (default: 50001)
- `ELECTRS_USE_SSL`: Whether to use SSL/TLS encryption (true/false)
- `ELECTRS_SSL_PORT`: Electrs SSL port (default: 50002)

### Umbrel Integration

For Umbrel users:
1. Enable the Bitcoin app on your Umbrel
2. The Electrs server typically runs on port 50001
3. Use your Umbrel's IP address as `ELECTRS_HOST`
4. Set `ELECTRS_USE_SSL=false` for local connections

Example `.env` for Umbrel:
```bash
ELECTRS_HOST=192.168.1.100  # Replace with your Umbrel's IP
ELECTRS_PORT=50001
ELECTRS_USE_SSL=false
ELECTRS_SSL_PORT=50002
```

## Benefits of Electrs Integration

- **Easier Setup**: No Bitcoin Core RPC credentials required
- **Better Performance**: Optimized for address and transaction queries
- **Umbrel Compatibility**: Works seamlessly with Umbrel's built-in Electrs
- **Index-Based Queries**: Faster lookups compared to Bitcoin Core RPC

## Notes
- This is a prototype; coinjoin handling and address heuristics can be improved
- Requires a synced Electrs server with full transaction indexing
- For production use, consider using SSL/TLS encryption