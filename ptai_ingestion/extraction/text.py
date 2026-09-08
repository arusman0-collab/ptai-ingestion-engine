from pathlib import Path
def extract_text(path: Path) -> tuple[str, dict]:
    data=path.read_bytes()
    for encoding in ("utf-8","utf-8-sig","latin-1"):
        try: return data.decode(encoding), {"method":"plain_text","encoding":encoding}
        except UnicodeDecodeError: pass
    raise ValueError("unable to decode text")