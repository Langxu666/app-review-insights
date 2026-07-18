#!/bin/bash
# ============================================================
# App Review Insights — Start Script (Linux / Mac)
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Done.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  App Review Insights — Starting Services${NC}"
echo -e "${GREEN}============================================================${NC}"

# ---- Check .env ----
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${YELLOW}Warning: $BACKEND_DIR/.env not found.${NC}"
    echo -e "${YELLOW}Copy .env.example to backend/.env and fill in your API key.${NC}"
    echo ""
fi

# ---- Check Python venv ----
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv "$BACKEND_DIR/venv"
    source "$BACKEND_DIR/venv/bin/activate"
    pip install -r "$BACKEND_DIR/requirements.txt"
else
    source "$BACKEND_DIR/venv/bin/activate"
fi

# ---- Check Node modules ----
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd "$FRONTEND_DIR"
    npm install
fi

# ---- Start Backend ----
echo -e "${GREEN}Starting backend on http://localhost:8000 ...${NC}"
cd "$BACKEND_DIR"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ---- Start Frontend ----
echo -e "${GREEN}Starting frontend on http://localhost:3000 ...${NC}"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Backend:  http://localhost:8000${NC}"
echo -e "${GREEN}  Frontend: http://localhost:3000${NC}"
echo -e "${GREEN}  Press Ctrl+C to stop all services${NC}"
echo -e "${GREEN}============================================================${NC}"

# Wait for either process to exit
wait