"""
PromptPay QR (Thai EMVCo payload). Static (no amount) or dynamic (with amount, one-time).
PROMPTPAY_ID may be a mobile number (0xxxxxxxxx) or a 13-digit tax/national id.
"""
from __future__ import annotations

import io

import qrcode


def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def _crc16(data: str) -> str:
    crc = 0xFFFF
    for ch in data.encode("ascii"):
        crc ^= ch << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def payload(promptpay_id: str, amount: float | None = None) -> str:
    pid = "".join(ch for ch in promptpay_id if ch.isdigit())
    if len(pid) == 13:
        account = _tlv("02", pid)                       # tax id / national id
    elif len(pid) == 15:
        account = _tlv("03", pid)                       # e-wallet id
    else:
        if pid.startswith("0"):
            pid = "66" + pid[1:]
        account = _tlv("01", pid.rjust(13, "0"))        # mobile: 0066 + 9 digits
    merchant = _tlv("29", _tlv("00", "A000000677010111") + account)
    body = _tlv("00", "01") + _tlv("01", "12" if amount else "11") + merchant + _tlv("53", "764")
    if amount:
        body += _tlv("54", f"{float(amount):.2f}")
    body += _tlv("58", "TH")
    body += "6304"
    return body + _crc16(body)


def png(promptpay_id: str, amount: float | None = None) -> bytes:
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    q.add_data(payload(promptpay_id, amount))
    q.make(fit=True)
    img = q.make_image(fill_color="#151667", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
