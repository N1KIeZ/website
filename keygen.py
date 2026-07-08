#!/usr/bin/env python3
"""Standalone license key generator — generates keys locally using RSA-style signing."""
import argparse
import secrets
from datetime import datetime

_CH = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
STATIC_D = 44411372526603278231981439147021640563272121446936530565914521287135611291649
STATIC_N = 59596791868544965917715049293139712060670803368525004046780554740535049298561


def _h(s):
    h = 0
    for c in s:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFFFFFFFFFF
    return h


def b32_encode(data):
    bits = "".join(f"{b:08b}" for b in data)
    padding = (5 - len(bits) % 5) % 5
    bits += "0" * padding
    return "".join(_CH[int(bits[i:i+5], 2)] for i in range(0, len(bits), 5))


def generate_key():
    prefix_chars = _CH[:-3]
    prefix = "".join(secrets.choice(prefix_chars) for _ in range(9))
    payload = prefix + "L"
    h = _h(payload)
    sig = pow(h, STATIC_D, STATIC_N)
    sig_bytes = sig.to_bytes((sig.bit_length() + 7) // 8, byteorder='big')
    sig_b32 = b32_encode(sig_bytes)
    raw_key = payload + sig_b32
    return "-".join(raw_key[i:i+5] for i in range(0, len(raw_key), 5))


def main():
    parser = argparse.ArgumentParser(description="Generate license keys")
    parser.add_argument("amount", nargs="?", type=int, default=10, help="Number of keys to generate (default: 10)")
    parser.add_argument("--output", "-o", help="Save keys to file (printed to stdout otherwise)")
    args = parser.parse_args()

    keys = []
    for _ in range(args.amount):
        keys.append(generate_key())

    if args.output:
        with open(args.output, "w") as f:
            for k in keys:
                f.write(k + "\n")
        print(f"Generated {len(keys)} keys -> {args.output}")
    else:
        print(f"\n{len(keys)} keys:\n")
        for k in keys:
            print(k)


if __name__ == "__main__":
    main()
