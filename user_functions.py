import json
import uuid
from pathlib import Path
from typing import Any, Callable, Set

def submit_support_ticket(email_address: str, description: str) -> str:
    """
    Submit a support ticket by creating a text file in the local directory.

    Args:
        email_address (str): The email address of the user submitting the ticket.
        description (str): A description of the issue.

    Returns:
        str: A JSON string confirming the support ticket creation and the file name.
    """
    # Get the directory where this script is located.
    script_dir = Path(__file__).parent
    
    # Generate a simple unique ticket number using part of a UUID.
    ticket_number = str(uuid.uuid4()).replace('-', '')[:6]
    file_name = f"ticket-{ticket_number}.txt"
    file_path = script_dir / file_name
    
    # Build the support ticket text.
    text = (
        f"Support ticket: {ticket_number}\n"
        f"Submitted by: {email_address}\n"
        "Description:\n"
        f"{description}"
    )
    file_path.write_text(text, encoding="utf-8")

    # Return a confirmation message in JSON format.
    message_json = json.dumps({
        "message": f"Support ticket {ticket_number} submitted. The ticket file is saved as {file_name}"
    })
    return message_json

# Set of available user functions; this can be extended in the future.
user_functions: Set[Callable[..., Any]] = { submit_support_ticket }

