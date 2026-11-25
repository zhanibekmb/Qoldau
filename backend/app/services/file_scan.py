"""ClamAV INSTREAM client. Missing or indeterminate verdicts fail closed."""
import socket
import struct

from ..config import Settings

EICAR = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"


class ScannerUnavailable(Exception):
    pass


def infected(data: bytes, settings: Settings) -> bool:
    if settings.effective_attachment_mode == "development":
        return EICAR in data or data.startswith(b"MZ")
    try:
        with socket.create_connection((settings.clamav_host, settings.clamav_port), timeout=5) as conn:
            conn.sendall(b"zINSTREAM\0")
            for start in range(0, len(data), 64 * 1024):
                chunk = data[start:start + 64 * 1024]
                conn.sendall(struct.pack(">I", len(chunk)) + chunk)
            conn.sendall(b"\0" * 4)
            reply = bytearray()
            while b"\0" not in reply and len(reply) < 4096:
                part = conn.recv(1024)
                if not part:
                    break
                reply.extend(part)
    except OSError as exc:
        raise ScannerUnavailable from exc

    result, terminator, _ = reply.partition(b"\0")
    if terminator and result == b"stream: OK":
        return False
    if terminator and result.startswith(b"stream: ") and result.endswith(b" FOUND"):
        return True
    raise ScannerUnavailable
