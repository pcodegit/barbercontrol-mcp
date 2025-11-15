#!/bin/bash

# BarberControl MCP Server Setup Script
# This script helps you set up the MCP server for local development

set -e

echo "======================================"
echo "BarberControl MCP Server Setup"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Check if we're in the mcp_server directory
if [ ! -f "barbercontrol.py" ]; then
    echo "❌ Please run this script from the mcp_server directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create .env file if it doesn't exist
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your Supabase credentials:"
    echo "   - NEXT_PUBLIC_SUPABASE_URL"
    echo "   - SUPABASE_SERVICE_ROLE_KEY"
    echo ""
    echo "   Get these from: Supabase Dashboard → Settings → API"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your .env file with Supabase credentials"
echo "   nano .env"
echo ""
echo "2. Run the MCP server:"
echo "   source venv/bin/activate"
echo "   python barbercontrol.py"
echo ""
echo "3. Or use FastMCP dev mode:"
echo "   source venv/bin/activate"
echo "   fastmcp dev barbercontrol.py"
echo ""
echo "4. Test with MCP Inspector:"
echo "   npm install -g @modelcontextprotocol/inspector"
echo "   mcp-inspector python barbercontrol.py"
echo ""
echo "5. Deploy to FastMCP Cloud:"
echo "   fastmcp login"
echo "   fastmcp deploy"
echo ""
