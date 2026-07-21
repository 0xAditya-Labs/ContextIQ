import os

def parse_tickets(filepath: str) -> list[dict]:
    """
    Reads the dummy IT tickets file, splits it into individual tickets (separated by blank lines),
    and returns a list of dictionaries for each ticket.
    
    Each dictionary contains:
    - ticket_id: str
    - category: str
    - issue: str
    - resolution: str
    - full_text: str
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by double newline to separate tickets
    # Handle both Windows \r\n and Unix \n line endings
    raw_tickets = [t.strip() for t in content.replace('\r\n', '\n').split('\n\n') if t.strip()]

    parsed_tickets = []
    for raw_ticket in raw_tickets:
        ticket_dict = {
            "ticket_id": "",
            "category": "",
            "issue": "",
            "resolution": "",
            "full_text": raw_ticket
        }
        
        lines = raw_ticket.split('\n')
        for line in lines:
            # Safely split by the first colon to extract key-value pairs
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == "ticket id":
                    ticket_dict["ticket_id"] = value
                elif key == "category":
                    ticket_dict["category"] = value
                elif key == "issue":
                    ticket_dict["issue"] = value
                elif key == "resolution":
                    ticket_dict["resolution"] = value
        
        # Only add valid tickets
        if ticket_dict["ticket_id"]:
            parsed_tickets.append(ticket_dict)
            
    return parsed_tickets
