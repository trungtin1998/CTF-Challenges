#!/bin/bash
set -e

# Start SQL Server in background
/opt/mssql/bin/sqlservr &

# Wait for SQL Server to start
echo "⏳ Waiting for SQL Server to be ready..."
sleep 20


# Run init.sql
echo "⚙️  Running init.sql..."
/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P 'sQrcHP!D5x' -C -i /init.sql

echo "✅ Initialization complete. Keeping SQL Server running..."

wait
