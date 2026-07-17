from __future__ import annotations

from io import BytesIO


def build_qr_svg(payload: str) -> str:
    import qrcode
    import qrcode.image.svg

    factory = qrcode.image.svg.SvgPathImage
    image = qrcode.make(payload, image_factory=factory, box_size=8, border=2)
    buffer = BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode("utf-8")