from base64 import b64encode
from io import BytesIO
import qrcode
import barcode
from barcode.writer import ImageWriter

def get_qr_code(data: str) -> str:
	qr_code_bytes = get_qr_code_bytes(data, format="PNG")
	base_64_string = bytes_to_base64_string(qr_code_bytes)

	return add_file_info(base_64_string)

def get_qr_code_bytes(data, format: str) -> bytes:
	"""Create a QR code and return the bytes."""
	img = qrcode.make(data)

	buffered = BytesIO()
	img.save(buffered, format=format)

	return buffered.getvalue()


def get_barcode(data: str) -> str:
    barcode_bytes = get_barcode_bytes(data, format="PNG")
    base_64_string = bytes_to_base64_string(barcode_bytes)

    return add_file_info(base_64_string)

def add_file_info(data: str) -> str:
    """Add info about the file type and encoding.
    
    This is required so the browser can make sense of the data."""
    return f"data:image/png;base64, {data}"

def get_barcode_bytes(data, format: str) -> bytes:
    """Create a Barcode and return the bytes."""
    code128 = barcode.get_barcode_class("code128")  # Using Code128 format
    barcode_instance = code128(data, writer=ImageWriter())

    buffered = BytesIO()
    barcode_instance.write(buffered, options={"format": format})

    return buffered.getvalue()

def bytes_to_base64_string(data: bytes) -> str:
    """Convert bytes to a base64 encoded string."""
    return b64encode(data).decode("utf-8")