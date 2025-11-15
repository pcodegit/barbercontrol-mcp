# BarberControl MCP Server Architecture

## System Overview

```
┌─────────────┐
│   Client    │
│  Calls In   │
└──────┬──────┘
       │
       │ Phone call
       ▼
┌─────────────────────────────┐
│   Voice Assistant           │
│   (External System)         │
│   - Speech-to-Text          │
│   - Natural Language        │
│   - Text-to-Speech          │
└──────────┬──────────────────┘
           │
           │ MCP Protocol (HTTPS)
           ▼
┌─────────────────────────────┐
│   FastMCP Cloud             │
│   ┌─────────────────────┐   │
│   │ barbercontrol.py    │   │
│   │ - get_barbers()     │   │
│   │ - check_avail()     │   │
│   │ - get_slots()       │   │
│   │ - book_appt()       │   │
│   └──────────┬──────────┘   │
└──────────────┼──────────────┘
               │
               │ Supabase Client (Service Role)
               ▼
┌─────────────────────────────┐
│   Supabase Database         │
│   ┌─────────────────────┐   │
│   │ • barbers           │   │
│   │ • availability_slots│   │
│   │ • appointments      │   │
│   │ • push_subscriptions│   │
│   └─────────────────────┘   │
│                             │
│   Triggers:                 │
│   • 2-client limit check    │
│   • Auto-update availability│
│   • Notification sender     │
└──────────────┬──────────────┘
               │
               │ Push Notification (optional)
               ▼
┌─────────────────────────────┐
│   Barber's Device           │
│   (BarberControl PWA)       │
│   - Receives notification   │
│   - Shows appointment       │
└─────────────────────────────┘
```

## Data Flow: Booking an Appointment

```
1. Client Calls
   ↓
2. Voice Agent Answers
   "Hi, how can I help you?"
   ↓
3. Client: "Book haircut for tomorrow at 2 PM"
   ↓
4. Voice Agent → MCP Tool: get_barbers()
   Response: [{ name: "Eduardo Pena", id: "e0c8..." }]
   ↓
5. Voice Agent → MCP Tool: check_barber_availability(
      barber_id: "e0c8...",
      date: "2025-01-21"
   )
   Response: "2:00 PM: 2 slots available"
   ↓
6. Voice Agent: "Can I have your name and phone?"
   Client: "John Doe, 555-1234"
   ↓
7. Voice Agent → MCP Tool: book_appointment(
      barber_id: "e0c8...",
      client_name: "John Doe",
      client_phone: "555-1234",
      date: "2025-01-21",
      time_slot: "2:00 PM"
   )
   ↓
8. Database:
   - Validates 2-client limit ✓
   - Creates appointment record
   - Updates availability_slots
   - Triggers push notification
   ↓
9. MCP Response: "✓ Appointment booked!"
   ↓
10. Voice Agent: "Your appointment is confirmed for
    tomorrow at 2 PM. Eduardo has been notified."
    ↓
11. Barber's Device:
    🔔 "New appointment: John Doe at 2:00 PM on 2025-01-21"
```

## Component Responsibilities

### Voice Assistant (External)
**Responsibilities:**
- Accept phone calls
- Convert speech to text
- Understand user intent
- Call appropriate MCP tools
- Convert responses to speech
- Handle conversation flow

**NOT responsible for:**
- Database access
- Business logic
- Appointment validation

### MCP Server (barbercontrol.py)
**Responsibilities:**
- Expose 4 tools via MCP protocol
- Validate input parameters
- Query Supabase database
- Format responses for voice
- Error handling

**NOT responsible for:**
- Authentication (uses service role)
- Database triggers (handled by Supabase)
- Push notification delivery (handled by app)

### Supabase Database
**Responsibilities:**
- Store barbers, slots, appointments
- Enforce 2-client-per-hour limit
- Auto-update slot availability
- Manage push subscriptions
- Row Level Security (RLS)

**NOT responsible for:**
- Voice processing
- User interface
- MCP protocol

## Security Model

```
┌─────────────────────┐
│  Voice Assistant    │
│  (No DB access)     │
└──────────┬──────────┘
           │
           │ MCP over HTTPS
           │ (No credentials)
           ▼
┌─────────────────────┐
│  MCP Server         │
│  (Service Role Key) │◄──── SUPABASE_SERVICE_ROLE_KEY
└──────────┬──────────┘       (Server-side only, never exposed)
           │
           │ Supabase Client
           │ (Full access)
           ▼
┌─────────────────────┐
│  Database           │
│  (RLS Policies)     │
└─────────────────────┘
```

**Security Principles:**
1. Service role key NEVER leaves the server
2. Voice assistant has NO direct database access
3. All operations go through validated MCP tools
4. Database enforces business rules via triggers
5. RLS policies provide defense in depth

## Error Handling Flow

```
User Request
    ↓
Voice Agent → MCP Tool
    ↓
┌───────────────────────┐
│ Input Validation      │
│ - Date format         │
│ - Required params     │
│ - Range limits        │
└─────┬─────────────────┘
      │
      ↓ Valid
┌───────────────────────┐
│ Database Query        │
└─────┬─────────────────┘
      │
      ↓ Success
┌───────────────────────┐
│ Business Logic        │
│ - 2-client check      │
│ - Slot availability   │
└─────┬─────────────────┘
      │
      ↓ Valid
┌───────────────────────┐
│ Execute Operation     │
└─────┬─────────────────┘
      │
      ↓
┌───────────────────────┐
│ Format Response       │
│ (Voice-friendly)      │
└───────────────────────┘

Any Error ──────────────────► User-Friendly Message
                              (Voice agent speaks it)
```

## Database Schema

```sql
-- Barbers (Users)
barbers
├── id (UUID, PK)
├── email (TEXT, UNIQUE)
├── name (TEXT)
├── phone (TEXT)
├── created_at (TIMESTAMPTZ)
└── updated_at (TIMESTAMPTZ)

-- Time Slots
availability_slots
├── id (UUID, PK)
├── barber_id (UUID, FK → barbers)
├── date (DATE)
├── time_slot (TEXT)  -- e.g., "9:00 AM"
├── is_available (BOOLEAN)
├── created_at (TIMESTAMPTZ)
└── updated_at (TIMESTAMPTZ)
    UNIQUE(barber_id, date, time_slot)

-- Appointments (2 per slot max)
appointments
├── id (UUID, PK)
├── barber_id (UUID, FK → barbers)
├── client_name (TEXT)
├── client_phone (TEXT)
├── client_email (TEXT, optional)
├── date (DATE)
├── time_slot (TEXT)
├── status (TEXT)  -- pending, confirmed, cancelled, completed, no_show
├── notes (TEXT, optional)
├── created_by (TEXT)  -- virtual_assistant, barber, client
├── created_at (TIMESTAMPTZ)
├── updated_at (TIMESTAMPTZ)
└── cancelled_at (TIMESTAMPTZ, optional)

-- Push Notifications
push_subscriptions
├── id (UUID, PK)
├── user_id (UUID, FK → auth.users)
├── endpoint (TEXT, UNIQUE)
├── p256dh_key (TEXT)
├── auth_key (TEXT)
├── created_at (TIMESTAMPTZ)
└── updated_at (TIMESTAMPTZ)
```

## Triggers & Constraints

### 1. Two-Client-Per-Hour Limit

**Trigger:** `check_max_appointments_trigger`
- Fires BEFORE INSERT/UPDATE on appointments
- Counts active appointments for slot
- Raises exception if count >= 2

```sql
IF appointment_count >= 2 THEN
  RAISE EXCEPTION 'Maximum 2 appointments per time slot'
END IF
```

### 2. Auto-Update Availability

**Trigger:** `auto_update_availability_trigger`
- Fires AFTER INSERT/UPDATE on appointments
- Updates availability_slots.is_available
- Sets FALSE when 2 appointments exist
- Sets TRUE when < 2 appointments

```sql
IF appointment_count >= 2 THEN
  UPDATE availability_slots SET is_available = FALSE
ELSE
  UPDATE availability_slots SET is_available = TRUE
END IF
```

## Deployment Architecture

### Local Development
```
Developer Machine
├── Python virtual environment
├── .env file (local secrets)
├── Direct Supabase connection
└── Test with mcp-inspector
```

### Production (FastMCP Cloud)
```
FastMCP Cloud Infrastructure
├── Managed Python runtime
├── Environment variables (encrypted)
├── HTTPS endpoint (auto-SSL)
├── Monitoring & logs
└── Auto-scaling
    ↓
    Connected to Supabase Production
```

## Monitoring Points

1. **FastMCP Dashboard**
   - Tool call frequency
   - Error rates
   - Response times
   - Active connections

2. **Supabase Dashboard**
   - Query performance
   - Table row counts
   - Active connections
   - Storage usage

3. **Voice Assistant Logs**
   - Conversation success rate
   - Most common requests
   - Error scenarios
   - User drop-off points

## Scaling Considerations

### Current Capacity
- **Barbers:** 1 (Eduardo)
- **Concurrent Clients:** Unlimited (per slot limits only)
- **Appointments per Hour:** 2 per barber
- **Database:** Supabase (PostgreSQL) - auto-scaling

### To Scale Up
1. **Add More Barbers:** Just create new barber accounts
2. **Increase Slot Capacity:** Adjust 2-client limit in triggers
3. **Add Locations:** Use location_id in schema
4. **Multiple Services:** Add service_type field

## API Rate Limits

**FastMCP Cloud (Free Tier):**
- 1000 requests/day
- 10 concurrent connections

**Supabase (Free Tier):**
- 500MB database
- 2GB bandwidth/month
- Unlimited API requests

**Upgrade paths available for both services**

## Disaster Recovery

### Backup Strategy
- Supabase: Automatic daily backups (7-day retention)
- Code: Version controlled in Git
- Environment variables: Documented in `.env.example`

### Recovery Procedure
1. Restore Supabase from backup
2. Redeploy MCP server from Git
3. Set environment variables
4. Verify with test booking

### Data Integrity
- All writes are transactional
- Triggers ensure consistency
- Soft deletes (status changes)
- Audit trail (created_at, updated_at)

---

This architecture enables scalable, reliable voice-powered appointment booking while maintaining security and data integrity.
