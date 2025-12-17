#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Define the usage function
usage() {
    echo -e "${CYAN}RAG Chatbot Runner${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --backend     Run Flask backend only (port 7860)"
    echo "  --frontend    Run React frontend only (port 3000)"
    echo "  --all         Run both backend and frontend (default)"
    echo "  --ngrok       Expose backend via ngrok"
    echo "  --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              # Run both backend and frontend"
    echo "  $0 --backend    # Run only Flask backend"
    echo "  $0 --frontend   # Run only React frontend"
    echo "  $0 --ngrok      # Run backend with ngrok tunnel"
    exit 0
}

# Kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        kill -9 $pid 2>/dev/null
        echo -e "${YELLOW}Stopped existing process on port $port (PID: $pid)${NC}"
        sleep 1
    fi
}

# Start Flask backend
start_backend() {
    echo -e "${GREEN}Starting Flask backend on port 5000...${NC}"

    cd "$PROJECT_ROOT"

    # Load environment variables from .env
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    fi

    # Activate virtual environment
    if [ -f ./venv/bin/activate ]; then
        source ./venv/bin/activate
    fi

    # Kill existing instance
    kill_port 7860

    # Run Flask backend
    if [[ -n $NGROK ]]; then
        python -m rag_chatbot --host localhost --port 7860 &
        BACKEND_PID=$!
        echo -e "${CYAN}Backend PID: $BACKEND_PID${NC}"
        ngrok http 7860
    else
        python -m rag_chatbot --host localhost --port 7860 &
        BACKEND_PID=$!
        echo -e "${CYAN}Backend PID: $BACKEND_PID${NC}"
        echo -e "${GREEN}Flask backend running at http://localhost:7860${NC}"
    fi
}

# Start React frontend
start_frontend() {
    echo -e "${GREEN}Starting React frontend on port 3000...${NC}"

    cd "$PROJECT_ROOT/frontend"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        npm install
    fi

    # Kill existing instance
    kill_port 3000

    # Run React frontend
    npm run dev &
    FRONTEND_PID=$!
    echo -e "${CYAN}Frontend PID: $FRONTEND_PID${NC}"
    echo -e "${GREEN}React frontend running at http://localhost:3000${NC}"
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${YELLOW}Stopped backend (PID: $BACKEND_PID)${NC}"
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${YELLOW}Stopped frontend (PID: $FRONTEND_PID)${NC}"
    fi
    # Also kill any orphaned processes on these ports
    kill_port 7860
    kill_port 3000
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup SIGINT SIGTERM

# Initialize variables
RUN_BACKEND=false
RUN_FRONTEND=false
NGROK=""
BACKEND_PID=""
FRONTEND_PID=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --backend)
            RUN_BACKEND=true
            shift
            ;;
        --frontend)
            RUN_FRONTEND=true
            shift
            ;;
        --all)
            RUN_BACKEND=true
            RUN_FRONTEND=true
            shift
            ;;
        --ngrok)
            NGROK=true
            RUN_BACKEND=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Default: run both if no specific option given
if [[ "$RUN_BACKEND" == false && "$RUN_FRONTEND" == false ]]; then
    RUN_BACKEND=true
    RUN_FRONTEND=true
fi

# Print banner
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════╗"
echo "║       RAG Chatbot - Deep Space Terminal   ║"
echo "╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# Start services
if [[ "$RUN_BACKEND" == true ]]; then
    start_backend
fi

if [[ "$RUN_FRONTEND" == true ]]; then
    # Give backend a moment to start
    if [[ "$RUN_BACKEND" == true ]]; then
        sleep 2
    fi
    start_frontend
fi

# Print status
echo ""
echo -e "${GREEN}Services started!${NC}"
if [[ "$RUN_BACKEND" == true ]]; then
    echo -e "  ${CYAN}Backend:${NC}  http://localhost:7860"
fi
if [[ "$RUN_FRONTEND" == true ]]; then
    echo -e "  ${CYAN}Frontend:${NC} http://localhost:3000"
fi
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Wait for background processes
wait
