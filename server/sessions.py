import threading
import uuid
from collections import OrderedDict

from py_swf.swf_parser import SWFFile

MAX_SESSIONS = 8

class OpenSwf:
    def __init__(self, filename, swf):
        self.filename = filename
        self.swf = swf
        self.dirty = False

class SessionRegistry:
    """In-memory LRU registry of open SWF files, keyed by session id."""

    def __init__(self, max_sessions=MAX_SESSIONS):
        self._sessions = OrderedDict()
        self._max = max_sessions
        self._lock = threading.Lock()

    def open(self, filename, file_bytes):
        swf = SWFFile()
        swf.read_bytes(file_bytes)
        sid = uuid.uuid4().hex
        with self._lock:
            self._sessions[sid] = OpenSwf(filename, swf)
            while len(self._sessions) > self._max:
                self._sessions.popitem(last=False)
        return sid

    def get(self, sid):
        with self._lock:
            session = self._sessions.get(sid)
            if session is None:
                raise KeyError(sid)
            self._sessions.move_to_end(sid)
            return session

    def close(self, sid):
        with self._lock:
            self._sessions.pop(sid, None)

registry = SessionRegistry()
