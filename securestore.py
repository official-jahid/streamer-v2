import json
import os
import subprocess
import tempfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from securebuffer import SecureBuffer

AAD = b'regix-config'


class SecureStore:
    def __init__(self, path, key_path):
        self.path = path
        self.key_path = key_path
        self._keybuf = SecureBuffer(32)
        self._keybuf.write(self._load_or_create_key())
        self._data = {}
        self.load()

    def _key(self):
        return self._keybuf.read()[:32]

    def _load_or_create_key(self):
        if os.path.exists(self.key_path):
            with open(self.key_path, 'rb') as f:
                key = f.read()
            if len(key) != 32:
                raise ValueError('invalid key file')
            return key
        key = os.urandom(32)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.key_path))
        os.close(fd)
        with open(tmp, 'wb') as f:
            f.write(key)
        os.replace(tmp, self.key_path)
        self._restrict_acl(self.key_path)
        return key

    @staticmethod
    def _restrict_acl(path):
        try:
            user = os.environ.get('USERNAME', 'Users')
            subprocess.run(
                ['icacls', path, '/inheritance:r', '/grant:r', f'{user}:F'],
                capture_output=True, timeout=10)
        except Exception:
            pass

    def load(self):
        if not os.path.exists(self.path):
            self._data = {}
            return
        with open(self.path, 'rb') as f:
            blob = f.read()
        if len(blob) < 28:
            self._data = {}
            return
        nonce, ct = blob[:12], blob[12:]
        try:
            plain = AESGCM(self._key()).decrypt(nonce, ct, AAD)
            self._data = json.loads(plain.decode('utf-8'))
        except Exception:
            self._data = {}

    def save(self):
        plain = json.dumps(self._data).encode('utf-8')
        nonce = os.urandom(12)
        ct = AESGCM(self._key()).encrypt(nonce, plain, AAD)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path))
        os.close(fd)
        with open(tmp, 'wb') as f:
            f.write(nonce + ct)
        os.replace(tmp, self.path)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def wipe_key(self):
        self._keybuf.wipe()