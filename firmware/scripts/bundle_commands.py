"""Replace only the Chinese FST command text in the generated ESP-SR image."""
import re
import struct


def bundle_commands(image, header, wake):
    entries = re.findall(r'^\s*\{(\d+), "([a-z ]+)",', header, re.MULTILINE)
    if [int(i) for i, _ in entries] != list(range(2, 18)):
        raise ValueError("Unexpected NOMI command IDs")
    if not re.fullmatch(r"[a-z]+(?: [a-z]+)*", wake):
        raise ValueError("Activation phrase must be lowercase space-separated pinyin")
    rows = [("1", wake), *entries, ("25", "da kai kong tiao")]
    if len({phrase for _, phrase in rows}) != len(rows):
        raise ValueError("Duplicate bundled command phrase")
    commands = "".join(f"{i},{phrase}\n" for i, phrase in rows).encode("ascii")

    offset = 4
    headers = bytearray(image[:offset])
    payload = bytearray()
    count, = struct.unpack_from("<I", image)
    replacements = 0
    records = []
    for _ in range(count):
        name, files = struct.unpack_from("<32sI", image, offset)
        headers.extend(image[offset:offset+36])
        offset += 36
        for _ in range(files):
            filename, start, size = struct.unpack_from("<32sII", image, offset)
            offset += 40
            if start + size > len(image):
                raise ValueError("Truncated ESP-SR model payload")
            data = image[start:start+size]
            if name.rstrip(b"\0") == b"fst" and filename.rstrip(b"\0") == b"commands_cn.txt":
                data = commands
                replacements += 1
            records.append((start, len(headers)))
            headers.extend(struct.pack("<32sII", filename, len(payload), len(data)))
            payload.extend(data)
    if replacements != 1 or any(start < offset for start, _ in records):
        raise ValueError("Unexpected ESP-SR model layout")
    for _, position in records:
        relative, = struct.unpack_from("<I", headers, position+32)
        struct.pack_into("<I", headers, position+32, len(headers)+relative)
    return bytes(headers + payload)
