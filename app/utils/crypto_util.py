import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise RuntimeError(
        "ENCRYPTION_KEY is not set. Generate one with "
        "`python -c \"from cryptography.fernet import Fernet; "
        "print(Fernet.generate_key().decode())\"` and add it to .env."
    )

# The key must stay fixed across restarts and worker processes, otherwise IDs
# encrypted by one process cannot be decrypted by another.
cipher_suite = Fernet(ENCRYPTION_KEY.encode())


def encrypt_data(data) -> str:
    return cipher_suite.encrypt(str(data).encode()).decode()


def decrypt_data(encrypted_data: str) -> int:
    return int(cipher_suite.decrypt(encrypted_data.encode()).decode())
