from io import BytesIO

from barcode.codex import Code128


def get_barcode_svg(
	data: str, module_width_mm: float = 0.2, module_height_mm: float = 15.0
) -> str:
	"""Create a QR code and return the bytes."""
	buffered = BytesIO()

	Code128(data).write(
		buffered,
		{
			"module_width": module_width_mm,
			"module_height": module_height_mm,
			"font_size": 0,  # Suppress subtitle text
			"quiet_zone": 0,  # Remove left and right white space
		},
	)

	return buffered.getvalue().decode()
