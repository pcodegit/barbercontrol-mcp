"""
BarberControl MCP Server
FastMCP server for voice assistant integration with BarberControl appointment system.
Enables external voice agents to check availability and book appointments.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
import httpx
from fastmcp import FastMCP
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("BarberControl Assistant")

# Initialize Supabase client with service role key
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing required environment variables: NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_expo_push_notification(
    tokens: list[str], title: str, body: str, data: dict | None = None
) -> int:
    """Send push notifications via Expo's push API. Returns count of successful sends."""
    if not tokens:
        return 0

    messages = [
        {
            "to": token,
            "sound": "default",
            "title": title,
            "body": body,
            **({"data": data} if data else {}),
        }
        for token in tokens
    ]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            EXPO_PUSH_URL,
            json=messages,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        result = response.json()

    sent = 0
    for ticket in result.get("data", []):
        if ticket.get("status") == "ok":
            sent += 1
    return sent


@mcp.tool()
def get_barbers() -> str:
    """
    Get list of all barbers in the system.
    Returns barber details including name, email, and phone.

    Returns:
        JSON string with list of barbers and their details
    """
    try:
        response = supabase.table("barbers").select("*").execute()

        if not response.data:
            return "No barbers found in the system."

        barbers = response.data
        result = f"Found {len(barbers)} barber(s):\n\n"

        for barber in barbers:
            result += f"- {barber['name']}\n"
            result += f"  ID: {barber['id']}\n"
            result += f"  Email: {barber['email']}\n"
            if barber.get('phone'):
                result += f"  Phone: {barber['phone']}\n"
            result += "\n"

        return result

    except Exception as e:
        return f"Error fetching barbers: {str(e)}"


@mcp.tool()
def check_barber_availability(barber_id: str, date: str) -> str:
    """
    Check availability for a specific barber on a specific date.
    Shows time slots and how many appointments are already booked per slot (max 2 per slot).

    Args:
        barber_id: UUID of the barber
        date: Date in YYYY-MM-DD format (e.g., "2025-01-15")

    Returns:
        JSON string with available time slots and booking counts
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return f"Invalid date format. Please use YYYY-MM-DD format (e.g., '2025-01-15')"

        # Get availability slots marked as available
        avail_response = supabase.table("availability_slots")\
            .select("time_slot")\
            .eq("barber_id", barber_id)\
            .eq("date", date)\
            .eq("is_available", True)\
            .execute()

        if not avail_response.data:
            return f"No availability slots found for barber {barber_id} on {date}. The barber may not be working this day."

        available_slots = [slot["time_slot"] for slot in avail_response.data]

        # Count appointments for each time slot
        appt_response = supabase.table("appointments")\
            .select("time_slot")\
            .eq("barber_id", barber_id)\
            .eq("date", date)\
            .in_("status", ["pending", "confirmed"])\
            .execute()

        # Build appointment counts
        appointment_counts = {}
        for appt in appt_response.data:
            time_slot = appt["time_slot"]
            appointment_counts[time_slot] = appointment_counts.get(time_slot, 0) + 1

        # Filter slots with < 2 appointments
        available_slots_with_info = []
        for time_slot in available_slots:
            booked = appointment_counts.get(time_slot, 0)
            if booked < 2:
                remaining = 2 - booked
                available_slots_with_info.append({
                    "time_slot": time_slot,
                    "booked": booked,
                    "remaining": remaining
                })

        if not available_slots_with_info:
            return f"All time slots are fully booked for {date}. Please try another date."

        # Format response for voice assistant
        result = f"Availability for {date}:\n\n"
        for slot_info in available_slots_with_info:
            result += f"- {slot_info['time_slot']}: {slot_info['remaining']} slot(s) available "
            result += f"({slot_info['booked']} already booked)\n"

        return result

    except Exception as e:
        return f"Error checking availability: {str(e)}"


@mcp.tool()
def get_available_slots(barber_id: str, start_date: str, end_date: str) -> str:
    """
    Get available time slots across a date range (useful for finding next available appointment).
    Shows slots with remaining capacity for each date.

    Args:
        barber_id: UUID of the barber
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        JSON string with available slots organized by date
    """
    try:
        # Validate date formats
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD format for both dates."

        if end_dt < start_dt:
            return "End date must be after start date."

        # Limit range to 30 days to prevent huge queries
        if (end_dt - start_dt).days > 30:
            return "Date range too large. Please limit to 30 days or less."

        # Get availability slots in range
        avail_response = supabase.table("availability_slots")\
            .select("date, time_slot")\
            .eq("barber_id", barber_id)\
            .gte("date", start_date)\
            .lte("date", end_date)\
            .eq("is_available", True)\
            .order("date")\
            .order("time_slot")\
            .execute()

        if not avail_response.data:
            return f"No availability found between {start_date} and {end_date}."

        # Get appointments in range
        appt_response = supabase.table("appointments")\
            .select("date, time_slot")\
            .eq("barber_id", barber_id)\
            .gte("date", start_date)\
            .lte("date", end_date)\
            .in_("status", ["pending", "confirmed"])\
            .execute()

        # Count appointments per date+time
        appointment_counts = {}
        for appt in appt_response.data:
            key = f"{appt['date']}_{appt['time_slot']}"
            appointment_counts[key] = appointment_counts.get(key, 0) + 1

        # Group available slots by date
        slots_by_date = {}
        for slot in avail_response.data:
            date = slot["date"]
            time_slot = slot["time_slot"]
            key = f"{date}_{time_slot}"
            booked = appointment_counts.get(key, 0)

            # Only include if not fully booked
            if booked < 2:
                if date not in slots_by_date:
                    slots_by_date[date] = []
                slots_by_date[date].append({
                    "time": time_slot,
                    "remaining": 2 - booked
                })

        if not slots_by_date:
            return f"No available slots found between {start_date} and {end_date}. All times are fully booked."

        # Format response
        result = f"Available slots from {start_date} to {end_date}:\n\n"
        for date in sorted(slots_by_date.keys()):
            result += f"{date}:\n"
            for slot in slots_by_date[date]:
                result += f"  - {slot['time']}: {slot['remaining']} slot(s) available\n"
            result += "\n"

        return result

    except Exception as e:
        return f"Error fetching available slots: {str(e)}"


@mcp.tool()
async def book_appointment(
    barber_id: str,
    client_name: str,
    client_phone: str,
    date: str,
    time_slot: str,
    client_email: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    Book an appointment for a client with a barber.
    Automatically sends push notification to the barber.
    Enforces 2-client-per-hour limit.

    Args:
        barber_id: UUID of the barber
        client_name: Full name of the client
        client_phone: Phone number of the client
        date: Appointment date in YYYY-MM-DD format
        time_slot: Time slot (e.g., "9:00 AM", "10:00 AM")
        client_email: Optional email address
        notes: Optional notes about the appointment

    Returns:
        Confirmation message with appointment details
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD format."

        # Check if slot is available
        avail_check = supabase.table("availability_slots")\
            .select("is_available")\
            .eq("barber_id", barber_id)\
            .eq("date", date)\
            .eq("time_slot", time_slot)\
            .execute()

        if not avail_check.data:
            return f"Time slot {time_slot} on {date} does not exist in the barber's schedule."

        if not avail_check.data[0]["is_available"]:
            return f"Time slot {time_slot} on {date} is not available."

        # Count existing appointments (2-client limit check)
        appt_count = supabase.table("appointments")\
            .select("id", count="exact")\
            .eq("barber_id", barber_id)\
            .eq("date", date)\
            .eq("time_slot", time_slot)\
            .in_("status", ["pending", "confirmed"])\
            .execute()

        if appt_count.count >= 2:
            return f"Time slot {time_slot} on {date} is fully booked (2 clients maximum per hour)."

        # Create appointment
        appointment_data = {
            "barber_id": barber_id,
            "client_name": client_name,
            "client_phone": client_phone,
            "date": date,
            "time_slot": time_slot,
            "status": "pending",
            "created_by": "virtual_assistant"
        }

        if client_email:
            appointment_data["client_email"] = client_email
        if notes:
            appointment_data["notes"] = notes

        insert_response = supabase.table("appointments")\
            .insert(appointment_data)\
            .execute()

        if not insert_response.data:
            return "Failed to create appointment. Please try again."

        appointment = insert_response.data[0]

        # Send push notification to barber
        try:
            subs_response = supabase.table("push_subscriptions")\
                .select("endpoint")\
                .eq("user_id", barber_id)\
                .eq("p256dh_key", "expo-push")\
                .execute()

            notification_status = ""
            if subs_response.data:
                tokens = [sub["endpoint"] for sub in subs_response.data]
                sent = await send_expo_push_notification(
                    tokens=tokens,
                    title="Nueva Cita Reservada",
                    body=f"{client_name} — {date} a las {time_slot}",
                    data={"appointmentId": appointment["id"]},
                )
                notification_status = f"\nPush notification sent to barber ({sent}/{len(tokens)} device(s))."
            else:
                notification_status = "\nNo push subscriptions found for barber."

        except Exception as notif_error:
            notification_status = f"\nNote: Push notification failed: {str(notif_error)}"

        # Format success response
        result = f"✓ Appointment booked successfully!\n\n"
        result += f"Confirmation Details:\n"
        result += f"- Appointment ID: {appointment['id']}\n"
        result += f"- Client: {client_name}\n"
        result += f"- Phone: {client_phone}\n"
        if client_email:
            result += f"- Email: {client_email}\n"
        result += f"- Date: {date}\n"
        result += f"- Time: {time_slot}\n"
        result += f"- Status: {appointment['status']}\n"
        if notes:
            result += f"- Notes: {notes}\n"
        result += notification_status

        return result

    except Exception as e:
        error_msg = str(e)
        # Check for trigger error (max appointments)
        if "Maximum 2 appointments per time slot" in error_msg:
            return f"Unable to book: Time slot {time_slot} on {date} is fully booked (2 clients maximum)."
        return f"Error booking appointment: {error_msg}"


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
