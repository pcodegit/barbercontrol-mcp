# BarberControl MCP Server

FastMCP server that enables voice assistants to interact with the BarberControl appointment system.

## Overview

This MCP server exposes 4 tools that allow external voice agents to:
- Query available barbers
- Check availability for specific dates
- View multi-day availability windows
- Book appointments and notify the barber

## Voice Assistant Integration Flow

```
Client calls → Voice Agent (external) → MCP Server → Supabase Database
                                          ↓
                                    Push notification to barber
```

## MCP Tools

### 1. `get_barbers()`
Lists all barbers in the system with their contact information.

**Returns:** List of barbers with ID, name, email, and phone

### 2. `check_barber_availability(barber_id, date)`
Check availability for a specific barber on a specific date.

**Parameters:**
- `barber_id` (string): UUID of the barber
- `date` (string): Date in YYYY-MM-DD format

**Returns:** Available time slots with booking counts (max 2 per slot)

### 3. `get_available_slots(barber_id, start_date, end_date)`
Get available slots across a date range (max 30 days).

**Parameters:**
- `barber_id` (string): UUID of the barber
- `start_date` (string): Start date in YYYY-MM-DD format
- `end_date` (string): End date in YYYY-MM-DD format

**Returns:** Available slots organized by date with remaining capacity

### 4. `book_appointment(barber_id, client_name, client_phone, date, time_slot, client_email?, notes?)`
Book an appointment for a client.

**Parameters:**
- `barber_id` (string): UUID of the barber
- `client_name` (string): Full name of the client
- `client_phone` (string): Phone number
- `date` (string): Date in YYYY-MM-DD format
- `time_slot` (string): Time slot (e.g., "9:00 AM")
- `client_email` (string, optional): Email address
- `notes` (string, optional): Appointment notes

**Returns:** Confirmation with appointment details

## Local Development

### 1. Install Dependencies

```bash
cd mcp_server
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in the `mcp_server/` directory:

```bash
cp .env.example .env
```

Edit `.env` with your Supabase credentials:
- `NEXT_PUBLIC_SUPABASE_URL`: From Supabase Dashboard → Settings → API
- `SUPABASE_SERVICE_ROLE_KEY`: From Supabase Dashboard → Settings → API → service_role key

⚠️ **Important:** The service role key bypasses Row Level Security. Keep it secret!

### 3. Run Locally

```bash
# Development mode
python barbercontrol.py

# Or using FastMCP CLI
fastmcp dev barbercontrol.py
```

### 4. Test with MCP Inspector

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector
mcp-inspector python barbercontrol.py
```

Visit http://localhost:6274 to test the tools interactively.

## Deployment to FastMCP Cloud

### Option 1: Deploy via GitHub

1. **Create GitHub Repository**
   ```bash
   cd mcp_server
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/barbercontrol-mcp.git
   git push -u origin main
   ```

2. **Deploy on FastMCP Cloud**
   - Visit https://fastmcp.com
   - Sign in with GitHub
   - Click "Deploy MCP Server"
   - Select your repository
   - Add environment variables:
     - `NEXT_PUBLIC_SUPABASE_URL`
     - `SUPABASE_SERVICE_ROLE_KEY`
   - Click "Deploy"

3. **Get Your MCP Endpoint**
   - Copy the generated MCP server URL
   - Use this in your voice assistant configuration

### Option 2: Deploy via CLI

1. **Install FastMCP CLI**
   ```bash
   pip install fastmcp
   ```

2. **Login to FastMCP**
   ```bash
   fastmcp login
   ```

3. **Deploy**
   ```bash
   fastmcp deploy
   ```

4. **Set Environment Variables**
   ```bash
   fastmcp env set NEXT_PUBLIC_SUPABASE_URL "https://your-project.supabase.co"
   fastmcp env set SUPABASE_SERVICE_ROLE_KEY "your-service-role-key"
   ```

## Connect Voice Assistant

After deployment, configure your voice assistant to use the MCP server:

### For Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "barbercontrol": {
      "url": "https://your-fastmcp-url.fastmcp.com"
    }
  }
}
```

### For Custom Voice Agent

Use the MCP client SDK in your voice agent:

```python
from mcp import Client

client = Client("https://your-fastmcp-url.fastmcp.com")

# Check availability
result = await client.call_tool("check_barber_availability", {
    "barber_id": "e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
    "date": "2025-01-20"
})

# Book appointment
result = await client.call_tool("book_appointment", {
    "barber_id": "e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
    "client_name": "John Doe",
    "client_phone": "555-1234",
    "date": "2025-01-20",
    "time_slot": "10:00 AM"
})
```

## Database Schema

The MCP server interacts with these Supabase tables:

- **barbers**: Barber information (id, name, email, phone)
- **availability_slots**: Time slots with availability status (2-client limit)
- **appointments**: Booked appointments with client details
- **push_subscriptions**: Push notification subscriptions for barbers

### 2-Client-Per-Hour Limit

The database enforces a maximum of 2 appointments per time slot using triggers:
- `check_max_appointments_trigger`: Prevents booking if 2 clients already booked
- `auto_update_availability_trigger`: Auto-marks slots unavailable when full

## Security

- Uses Supabase service role key for database access
- All database operations respect existing RLS policies
- Environment variables are never exposed in responses
- Push notifications are sent securely via Supabase

## Troubleshooting

### "Missing required environment variables"
- Ensure `.env` file exists with correct variables
- On FastMCP Cloud, verify environment variables are set in dashboard

### "No availability found"
- Check that barber has created availability slots in the BarberControl app
- Verify `is_available` is set to `true` for the time slots
- Confirm date format is YYYY-MM-DD

### "Time slot is fully booked"
- Maximum 2 clients per hour is enforced
- Check existing appointments for that time slot
- Suggest alternative time slots to the client

### Push notifications not working
- Verify barber has subscribed to push notifications in the app
- Check `push_subscriptions` table has entries for the barber
- Notification sending requires additional web-push setup (optional)

## Monitoring

### FastMCP Cloud Dashboard
- View logs at https://fastmcp.com/dashboard
- Monitor tool usage and errors
- Check response times

### Supabase Dashboard
- View appointments in Database → Tables → appointments
- Check availability slots in availability_slots table
- Monitor push subscriptions

## Support

For issues or questions:
- FastMCP Documentation: https://docs.fastmcp.com
- Supabase Documentation: https://supabase.com/docs
- GitHub Issues: [Your repository URL]

## License

[Your License Here]
