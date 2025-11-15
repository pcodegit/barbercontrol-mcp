# Testing the BarberControl MCP Server

This guide helps you test the MCP server locally before deploying to production.

## Current Database State

**Barber:**
- Name: Eduardo Pena
- ID: `e0c8c546-b205-4fbf-bf89-e0dce022fdb0`
- Email: josepena.dev91@gmail.com

**Availability Slots:** 17 slots exist (check availability status in app)

**Appointments:** Currently 0 appointments

## Quick Test Commands

### 1. Test with MCP Inspector (Recommended)

Install and run the MCP Inspector:

```bash
npm install -g @modelcontextprotocol/inspector
cd mcp_server
source venv/bin/activate
mcp-inspector python barbercontrol.py
```

Visit http://localhost:6274 and test each tool interactively.

### 2. Test with Python Script

Create a test script `test_mcp.py`:

```python
import asyncio
from barbercontrol import get_barbers, check_barber_availability, get_available_slots, book_appointment

async def test_tools():
    # Test 1: Get barbers
    print("=== Test 1: Get Barbers ===")
    result = get_barbers()
    print(result)
    print()

    # Test 2: Check availability for today
    print("=== Test 2: Check Availability ===")
    result = check_barber_availability(
        barber_id="e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
        date="2025-01-20"  # Update to a date with availability
    )
    print(result)
    print()

    # Test 3: Get available slots for next 7 days
    print("=== Test 3: Get Available Slots (7 days) ===")
    result = get_available_slots(
        barber_id="e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
        start_date="2025-01-20",
        end_date="2025-01-27"
    )
    print(result)
    print()

    # Test 4: Book appointment (use a real available slot)
    print("=== Test 4: Book Appointment ===")
    result = book_appointment(
        barber_id="e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
        client_name="Test Client",
        client_phone="555-1234",
        date="2025-01-20",
        time_slot="10:00 AM",  # Use an available slot
        client_email="test@example.com",
        notes="Test appointment via MCP"
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(test_tools())
```

Run the test:

```bash
cd mcp_server
source venv/bin/activate
python test_mcp.py
```

## Voice Assistant Test Scenarios

### Scenario 1: Check Next Available Slot

**User says:** "When is the next available appointment?"

**Voice agent should:**
1. Call `get_barbers()` to get barber ID
2. Call `get_available_slots(barber_id, today, today+7days)`
3. Find the earliest available slot
4. Respond: "The next available appointment is [date] at [time]"

### Scenario 2: Book Specific Time

**User says:** "Book me for tomorrow at 2 PM"

**Voice agent should:**
1. Calculate tomorrow's date (YYYY-MM-DD)
2. Convert "2 PM" to "2:00 PM" format
3. Call `check_barber_availability(barber_id, tomorrow)`
4. Verify "2:00 PM" is available
5. Call `book_appointment()` with user details
6. Confirm: "Your appointment is booked for [date] at 2:00 PM"

### Scenario 3: Find Availability This Week

**User says:** "What times are available this week?"

**Voice agent should:**
1. Calculate start_date (today) and end_date (7 days from now)
2. Call `get_available_slots(barber_id, start_date, end_date)`
3. List all available times grouped by day

### Scenario 4: Handle Fully Booked Slot

**User says:** "Book me for [date] at [time]"

**Voice agent should:**
1. Call `check_barber_availability(barber_id, date)`
2. If slot has 0 remaining, suggest alternative times
3. If slot is not in available list, explain barber is not working

## Testing Edge Cases

### Edge Case 1: 2-Client Limit

```python
# Book first appointment
book_appointment(
    barber_id="e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
    client_name="Client 1",
    client_phone="555-0001",
    date="2025-01-20",
    time_slot="10:00 AM"
)

# Book second appointment (should succeed)
book_appointment(
    barber_id="e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
    client_name="Client 2",
    client_phone="555-0002",
    date="2025-01-20",
    time_slot="10:00 AM"
)

# Try to book third appointment (should fail)
book_appointment(
    barber_id="e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
    client_name="Client 3",
    client_phone="555-0003",
    date="2025-01-20",
    time_slot="10:00 AM"
)
# Expected: "Time slot is fully booked (2 clients maximum)"
```

### Edge Case 2: Invalid Date Format

```python
check_barber_availability(
    barber_id="e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
    date="01/20/2025"  # Wrong format
)
# Expected: "Invalid date format. Please use YYYY-MM-DD format"
```

### Edge Case 3: Date Range Too Large

```python
get_available_slots(
    barber_id="e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
    start_date="2025-01-01",
    end_date="2025-03-01"  # 60 days
)
# Expected: "Date range too large. Please limit to 30 days or less."
```

### Edge Case 4: Slot Not in Schedule

```python
book_appointment(
    barber_id="e0c8c546-b205-4fbf-bf89-e0dce022fdb0",
    client_name="Test",
    client_phone="555-1234",
    date="2025-01-20",
    time_slot="3:30 AM"  # Non-existent slot
)
# Expected: "Time slot does not exist in the barber's schedule"
```

## Testing Checklist

Before deploying to production:

- [ ] All 4 tools execute without errors
- [ ] Date validation works correctly
- [ ] 2-client-per-hour limit is enforced
- [ ] Appointments save to database
- [ ] Error messages are voice-friendly
- [ ] Push notifications attempt to send
- [ ] Invalid inputs return helpful error messages
- [ ] Date ranges respect 30-day limit

## Monitoring in Production

After deploying to FastMCP Cloud:

1. **FastMCP Dashboard**
   - Check tool usage statistics
   - Review error logs
   - Monitor response times

2. **Supabase Dashboard**
   - Verify appointments are being created
   - Check appointment status values
   - Monitor push_subscriptions table

3. **Voice Assistant Logs**
   - Check MCP tool call success rates
   - Review conversation flows
   - Identify common user requests

## Common Issues

### Issue: "No availability found"
**Solution:** Create availability slots in the BarberControl app first

### Issue: "Missing required environment variables"
**Solution:** Verify `.env` file exists with correct Supabase credentials

### Issue: "Time slot does not exist"
**Solution:** Ensure time_slot format matches exactly (e.g., "10:00 AM" not "10am")

### Issue: Push notifications not sending
**Solution:**
- Barber must subscribe to notifications in the app
- Check push_subscriptions table has entries
- Web-push library setup may be needed for actual sending

## Next Steps

1. Test all tools locally
2. Create availability slots in BarberControl app
3. Deploy to FastMCP Cloud
4. Connect voice assistant
5. Monitor production usage
6. Iterate based on user feedback
