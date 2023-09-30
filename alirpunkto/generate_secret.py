# This script is used to generate a secret key for Fernet when executed as a standalone script.
# When imported in alirpunkto, it verifies library compatibility.
# author: Michaël Launay
# date: 2023-09-30

import os
import sys
import secrets
import base64
from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = secrets.token_bytes(32)
    key_base64 = base64.urlsafe_b64encode(key)
    print(f"""SECRET_KEY="{key_base64.decode('utf-8')}" """)