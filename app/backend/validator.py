import re
from fastapi import HTTPException, status

def validate_ip_address(ip: str) -> None:
    """Validate IP address or raise HTTPException"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    if not re.match(pattern, ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid IP format: {ip}"
        )
    
    octets = ip.split('.')
    for octet in octets:
        if int(octet) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid IP: octets must be 0-255"
            )
