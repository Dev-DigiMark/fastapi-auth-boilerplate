# from cryptography.fernet import Fernet
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # Generate a key using `Fernet.generate_key()` and save it in .env as ENCRYPTION_KEY
# ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
# fernet = Fernet(ENCRYPTION_KEY.encode())

# def encrypt_data(data: int) -> str:
#     """
#     Encrypt data using Fernet.
#     """
#     return fernet.encrypt(data.encode()).decode()

# def decrypt_data(encrypted_data: str) -> str:
#     """
#     Decrypt data using Fernet.
#     """
#     return fernet.decrypt(encrypted_data.encode()).decode()


from cryptography.fernet import Fernet

# Example encryption and decryption using Fernet (symmetric encryption)
# You can replace this with any encryption method you prefer

# Generate a key (this should be stored securely)
key = Fernet.generate_key()
cipher_suite = Fernet(key)

def encrypt_data(data: int) -> str:
    # Convert the integer to string and encrypt it
    data_str = str(data)
    encrypted_data = cipher_suite.encrypt(data_str.encode())
    return encrypted_data.decode()  # Return as a string

def decrypt_data(encrypted_data: str) -> int:
    # Decrypt the data and convert it back to an integer
    decrypted_data = cipher_suite.decrypt(encrypted_data.encode()).decode()
    return int(decrypted_data)
