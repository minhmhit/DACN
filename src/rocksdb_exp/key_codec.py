#!/usr/bin/env python3
"""
21-Byte Unsigned Big-Endian Binary Composite Key Codec
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
(PostgreSQL B-Tree vs. RocksDB LSM-Tree)

Key Encodings:
1. K_opt (Optimal leftmost prefix order):
   [tenant_id: 4B uint32_be] + [status: 1B uint8] + [created_at: 8B uint64_be] + [order_id: 8B uint64_be] = 21B
2. K_inv (Inverted low-selectivity leading order):
   [status: 1B uint8] + [created_at: 8B uint64_be] + [tenant_id: 4B uint32_be] + [order_id: 8B uint64_be] = 21B
"""

from __future__ import annotations

import struct
from typing import NamedTuple, Tuple

# Binary layout definitions
# K_opt: > I (4B) B (1B) Q (8B) Q (8B) = 21 Bytes
K_OPT_FORMAT = ">IBQQ"
# K_inv: > B (1B) Q (8B) I (4B) Q (8B) = 21 Bytes
K_INV_FORMAT = ">BQI Q".replace(" ", "")

# Value format: > i (4B amount) 100s (100B ASCII payload) = 104 Bytes
VALUE_FORMAT = ">i100s"

KEY_SIZE_BYTES = 21
VALUE_SIZE_BYTES = 104


class DecodedKey(NamedTuple):
    tenant_id: int
    status: int
    created_at: int
    order_id: int


def encode_k_opt(tenant_id: int, status: int, created_at: int, order_id: int) -> bytes:
    """Encodes K_opt: [tenant_id (4B)][status (1B)][created_at (8B)][order_id (8B)]."""
    return struct.pack(K_OPT_FORMAT, tenant_id, status, created_at, order_id)


def decode_k_opt(key_bytes: bytes) -> DecodedKey:
    """Decodes 21-byte K_opt binary key."""
    if len(key_bytes) != KEY_SIZE_BYTES:
        raise ValueError(
            f"Expected {KEY_SIZE_BYTES} bytes for K_opt, got {len(key_bytes)}"
        )
    t_id, st, cr_at, o_id = struct.unpack(K_OPT_FORMAT, key_bytes)
    return DecodedKey(
        tenant_id=t_id, status=st, created_at=cr_at, order_id=o_id
    )


def encode_k_inv(tenant_id: int, status: int, created_at: int, order_id: int) -> bytes:
    """Encodes K_inv: [status (1B)][created_at (8B)][tenant_id (4B)][order_id (8B)]."""
    return struct.pack(K_INV_FORMAT, status, created_at, tenant_id, order_id)


def decode_k_inv(key_bytes: bytes) -> DecodedKey:
    """Decodes 21-byte K_inv binary key."""
    if len(key_bytes) != KEY_SIZE_BYTES:
        raise ValueError(
            f"Expected {KEY_SIZE_BYTES} bytes for K_inv, got {len(key_bytes)}"
        )
    st, cr_at, t_id, o_id = struct.unpack(K_INV_FORMAT, key_bytes)
    return DecodedKey(
        tenant_id=t_id, status=st, created_at=cr_at, order_id=o_id
    )


def encode_k_opt_prefix_4b(tenant_id: int) -> bytes:
    """4-byte prefix matching SliceTransform for K_opt."""
    return struct.pack(">I", tenant_id)


def encode_k_opt_seek_start(tenant_id: int, status: int, created_at_start: int) -> bytes:
    """Seek lower bound key for K_opt prefix range scan."""
    return struct.pack(K_OPT_FORMAT, tenant_id, status, created_at_start, 0)


def encode_k_opt_seek_end(tenant_id: int, status: int, created_at_end: int) -> bytes:
    """Seek upper bound key for K_opt prefix range scan."""
    return struct.pack(
        K_OPT_FORMAT, tenant_id, status, created_at_end, 0xFFFFFFFFFFFFFFFF
    )


def encode_k_inv_seek_start(status: int, created_at_start: int) -> bytes:
    """Seek lower bound key for K_inv range scan (without tenant_id prefix)."""
    return struct.pack(K_INV_FORMAT, status, created_at_start, 0, 0)


def encode_k_inv_seek_end(status: int, created_at_end: int) -> bytes:
    """Seek upper bound key for K_inv range scan."""
    return struct.pack(
        K_INV_FORMAT,
        status,
        created_at_end,
        0xFFFFFFFF,
        0xFFFFFFFFFFFFFFFF,
    )


def encode_order_value(amount: int, payload_str: str) -> bytes:
    """Encodes order value: 4-byte amount + 100-byte ASCII payload."""
    payload_bytes = payload_str.encode("ascii")[:100].ljust(100, b" ")
    return struct.pack(VALUE_FORMAT, amount, payload_bytes)


def decode_order_value(value_bytes: bytes) -> Tuple[int, str]:
    """Decodes order value into (amount, payload_str)."""
    amount, p_bytes = struct.unpack(VALUE_FORMAT, value_bytes)
    return amount, p_bytes.decode("ascii", errors="replace").rstrip()
