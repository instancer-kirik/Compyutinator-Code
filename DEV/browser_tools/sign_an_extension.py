from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import json
from cryptography.hazmat.primitives import serialization
#b. Sign an extension (do this for each extension):
# Load the private key 
with open("private_key.pem", "rb") as key_file:
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=b'passphrase'
    )

# Sign the manifest
with open("manifest.json", "rb") as f:
    manifest_data = f.read()

signature = private_key.sign(
    manifest_data,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH
    ),
    hashes.SHA256()
)

# Save the signature
with open("signature.bin", "wb") as f:
    f.write(signature)