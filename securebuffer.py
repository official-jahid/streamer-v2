import ctypes

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]
kernel32.VirtualLock.restype = ctypes.c_int
kernel32.VirtualLock.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
kernel32.VirtualUnlock.restype = ctypes.c_int
kernel32.VirtualUnlock.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
kernel32.VirtualFree.restype = ctypes.c_int
kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32]


class SecureBuffer:
    def __init__(self, size):
        self.size = size
        self._ptr = kernel32.VirtualAlloc(None, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        if not self._ptr:
            raise ctypes.WinError(ctypes.get_last_error())
        self._locked = bool(kernel32.VirtualLock(self._ptr, size))
        self._wiped = False

    def write(self, data):
        if len(data) > self.size:
            raise ValueError('data exceeds buffer size')
        ctypes.memmove(self._ptr, data, len(data))

    def read(self):
        return ctypes.string_at(self._ptr, self.size)

    def wipe(self):
        if self._ptr and not self._wiped:
            ctypes.memset(self._ptr, 0, self.size)
            self._wiped = True

    def close(self):
        if self._ptr:
            self.wipe()
            if self._locked:
                kernel32.VirtualUnlock(self._ptr, self.size)
            kernel32.VirtualFree(self._ptr, 0, MEM_RELEASE)
            self._ptr = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass