"""XOR-encrypt cheat_payload.bin in-place."""
import os

# Must match the key in main.cpp exactly
XOR_KEY = bytes([
    0xAB, 0xCD, 0xEF, 0x01, 0x23, 0x45, 0x67, 0x89,
    0xBA, 0xDC, 0xFE, 0x10, 0x32, 0x54, 0x76, 0x98,
    0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE, 0xBA, 0xBE,
])

payload_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "predatorGUI\\examples\\example_win32_directx9\\cheat_payload.bin",
)
payload_path = os.path.normpath(payload_path)

with open(payload_path, "rb") as f:
    data = bytearray(f.read())

for i in range(len(data)):
    data[i] ^= XOR_KEY[i % len(XOR_KEY)]

with open(payload_path, "wb") as f:
    f.write(data)

print(f"Encrypted {len(data)} bytes in {payload_path}")
