#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════╗"
echo "║       RAG Chatbot - Installation          ║"
echo "╚═══════════════════════════════════════════╝"
echo -e "${NC}"

cd "$PROJECT_ROOT"

# Install Python dependencies
echo -e "${GREEN}Installing Python dependencies...${NC}"
pip install .

# Install frontend dependencies
echo -e "${GREEN}Installing frontend dependencies...${NC}"
if [ -d "frontend" ]; then
    cd frontend
    if command -v npm &> /dev/null; then
        npm install
        echo -e "${GREEN}Frontend dependencies installed!${NC}"
    else
        echo -e "${YELLOW}npm not found. Please install Node.js to use the React frontend.${NC}"
    fi
    cd ..
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo -e "To start the application, run:"
echo -e "  ${CYAN}./scripts/run.sh${NC}           # Start both backend and frontend"
echo -e "  ${CYAN}./scripts/run.sh --backend${NC} # Start only Flask backend"
echo -e "  ${CYAN}./scripts/run.sh --frontend${NC} # Start only React frontend"
