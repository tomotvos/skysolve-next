# skysolve_next/publish/lx200_server.py
import socket
import threading
import time
import logging
import binascii
from typing import Optional, Deque
from collections import deque
from skysolve_next.core.config import settings
from skysolve_next.core.models import SolveResult

# --- Logging setup (safe default) ---
_logger = logging.getLogger("skysolve.lx200")
if not _logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _logger.addHandler(h)
_logger.setLevel(logging.DEBUG)

# --- Rotating in-memory debug store (and persisted tail) ---
_DEBUG_LOG_PATH = "/tmp/skysolve-lx200-debug.log"
_debug_store: Deque[str] = deque(maxlen=200)

def _debug_persist(text: str) -> None:
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass

def _record_debug(text: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {text}"
    _debug_store.append(line)
    _debug_persist(line)

# --- LX200 server implementation ---
class LX200Server:
    """Robust read-only LX200 server for SkySafari.
    Publishes latest solved RA/Dec; ignores movement commands.
    """

    def __init__(self, host: str = "0.0.0.0", port: Optional[int] = None) -> None:
        self.port = port or settings.lx200_port
        self.host = host
        self._server: Optional[socket.socket] = None
        self._last: Optional[SolveResult] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(8)
        self._server = s
        threading.Thread(target=self._accept_loop, daemon=True).start()
        _logger.info("LX200 server listening on %s:%d", self.host, self.port)
        _record_debug(f"LX200 server started on {self.host}:{self.port}")

    def _accept_loop(self) -> None:
        while True:
            try:
                conn, addr = self._server.accept()
            except Exception as e:
                _logger.exception("accept failed: %s", e)
                time.sleep(0.5)
                continue
            _logger.info("Accepted connection from %s:%d", addr[0], addr[1])
            _record_debug(f"ACCEPT {addr[0]}:{addr[1]}")
            t = threading.Thread(target=self._client_loop, args=(conn, addr), daemon=True)
            t.start()

    def _client_loop(self, conn: socket.socket, addr) -> None:
        conn.settimeout(15)
        buf = ""
        try:
            while True:
                try:
                    chunk = conn.recv(4096)
                except socket.timeout:
                    # continue to keep connection alive; SkySafari often polls
                    continue
                if not chunk:
                    break
                # log raw bytes
                hexb = binascii.hexlify(chunk).decode()
                txt = chunk.decode(errors="replace")
                _logger.debug("recv %d bytes from %s:%d -> hex=%s text=%r", len(chunk), addr[0], addr[1], hexb, txt)
                _record_debug(f"RECV {addr[0]}:{addr[1]} HEX={hexb} TXT={txt!r}")

                buf += txt
                # process commands delimited by '#'
                while True:
                    idx = buf.find("#")
                    if idx == -1:
                        break
                    raw = buf[: idx + 1]
                    buf = buf[idx + 1 :]
                    cmd = raw.strip()
                    if not cmd:
                        continue
                    if not cmd.startswith(":"):
                        cmd = ":" + cmd
                    _logger.debug("parsed cmd=%r from %s:%d", cmd, addr[0], addr[1])
                    _record_debug(f"CMD {addr[0]}:{addr[1]} {cmd}")
                    self._handle_command(conn, cmd)
        except Exception as e:
            _logger.exception("client loop error for %s:%d: %s", addr[0], addr[1], e)
        finally:
            try:
                conn.close()
            except Exception:
                pass
            _logger.info("Connection closed %s:%d", addr[0], addr[1])
            _record_debug(f"CLOSE {addr[0]}:{addr[1]}")

    def _send_and_log(self, conn: socket.socket, resp: bytes) -> None:
        try:
            conn.sendall(resp)
        except Exception:
            _logger.exception("failed to send reply")
        _logger.debug("sent %d bytes -> hex=%s text=%r", len(resp), binascii.hexlify(resp).decode(), resp.decode(errors="replace"))
        _record_debug(f"SEND HEX={binascii.hexlify(resp).decode()} TXT={resp.decode(errors='replace')!r}")

    def _handle_command(self, conn: socket.socket, cmd: str) -> None:
        # READ QUERIES
        # Accept both :GR# and :RS# (SkySafari variations), and lowercase forms.
        if cmd.upper().startswith(":GR#") or cmd.upper().startswith(":RS#"):  # Get RA
            # If we haven't published a solve yet, return a benign zero RA (avoid returning '#')
            ra_val = (self._last.ra_deg if self._last and getattr(self._last, "ra_deg", None) is not None else 0.0)
            ra = self._format_ra(ra_val)
            self._send_and_log(conn, (ra + "#").encode())
            return
        if cmd.upper().startswith(":GD#"):  # Get Dec
            dec_val = (self._last.dec_deg if self._last and getattr(self._last, "dec_deg", None) is not None else 0.0)
            dec = self._format_dec(dec_val)
            self._send_and_log(conn, (dec + "#").encode())
            return
        if cmd.startswith(":GVP#"):
            self._send_and_log(conn, b"Skysolve Next#")
            return
        if cmd.startswith(":GVN#"):
            self._send_and_log(conn, b"0.1#")
            return
        if cmd.startswith(":GVD#") or cmd.startswith(":GC#"):
            self._send_and_log(conn, time.strftime("%m/%d/%y").encode() + b"#")
            return
        if cmd.startswith(":GVT#") or cmd.startswith(":GL#"):
            self._send_and_log(conn, time.strftime("%H:%M:%S").encode() + b"#")
            return
        if cmd.startswith(":U#"):
            # high precision toggle ack
            self._send_and_log(conn, b"1")
            return

        # SETTERS (ACK ONLY)
        if cmd.startswith(":SC"):   # set date
            self._send_and_log(conn, b"1")
            return
        if cmd.startswith(":SL"):   # set time
            self._send_and_log(conn, b"1")
            return
        if cmd.startswith(":St") or cmd.startswith(":Sg"):  # set site lat/long
            self._send_and_log(conn, b"1")
            return

        # SLEW/MOTION (IGNORED)
        if cmd.startswith(":MS#") or cmd.startswith(":Mn#") or cmd.startswith(":Me#") or cmd.startswith(":Ms#") or cmd.startswith(":Mw#"):
            self._send_and_log(conn, b"0")
            return

        # Default reply per Meade: '#'
        self._send_and_log(conn, b"#")

    def publish(self, result: SolveResult) -> None:
        with self._lock:
            self._last = result
            conf_val = getattr(result,'confidence',None)
            conf_str = conf_val if conf_val not in (None, 0.0) else "-"
            ra_str = f"{result.ra_deg:.6f}" if getattr(result, 'ra_deg', None) is not None else "-"
            dec_str = f"{result.dec_deg:.6f}" if getattr(result, 'dec_deg', None) is not None else "-"
            _record_debug(f"PUB RA={ra_str} DEC={dec_str} CONF={conf_str}")

    @staticmethod
    def _format_ra(ra_deg: float) -> str:
        hours = ra_deg / 15.0
        h = int(hours); m = int((hours - h) * 60); s = int((((hours - h) * 60) - m) * 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @staticmethod
    def _format_dec(dec_deg: float) -> str:
        sign = "+" if dec_deg >= 0 else "-"; v = abs(dec_deg)
        d = int(v); m = int((v - d) * 60); s = int((((v - d) * 60) - m) * 60)
        return f"{sign}{d:02d}*{m:02d}:{s:02d}"

# Optional helper to dump last debug lines (useful from a shell)
def dump_debug_tail(n: int = 80):
    print("\n".join(list(_debug_store)[-n:]))
