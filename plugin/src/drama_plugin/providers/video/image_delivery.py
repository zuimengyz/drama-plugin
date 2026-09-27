"""Seedance image wire encoding; formal Media identity remains Host-owned."""
import base64
import binascii
import ipaddress
from urllib.parse import urlsplit


def external_https(url: str) -> bool:
    p = urlsplit(url)
    host = (p.hostname or '').lower().rstrip('.')
    if p.scheme != 'https' or not host or p.username or p.password or host == 'localhost' or host.endswith(('.localhost', '.local')):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return '.' in host


def image_mime(data: bytes) -> str:
    if data.startswith(b'\x89PNG\r\n\x1a\n'): return 'image/png'
    if data.startswith(b'\xff\xd8\xff'): return 'image/jpeg'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP': return 'image/webp'
    if data[:6] in (b'GIF87a', b'GIF89a'): return 'image/gif'
    if data.startswith(b'BM'): return 'image/bmp'
    if data[:4] in (b'II*\x00', b'MM\x00*'): return 'image/tiff'
    raise ValueError('SEEDANCE_IMAGE_MIME_UNSUPPORTED')


def image_data_url(data: bytes, mime: str) -> str:
    if image_mime(data) != mime:
        raise ValueError('REFERENCE_IMAGE_MIME_MISMATCH')
    return 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')


def decode_image_url(url: str) -> bytes:
    header, sep, encoded = url.partition(',')
    if not sep or not header.startswith('data:image/') or not header.endswith(';base64'):
        raise ValueError('SEEDANCE_IMAGE_DATA_URL_INVALID')
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError('SEEDANCE_IMAGE_DATA_URL_INVALID') from exc
    if image_mime(data) != header[5:-7]:
        raise ValueError('REFERENCE_IMAGE_MIME_MISMATCH')
    return data
