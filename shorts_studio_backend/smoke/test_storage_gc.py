from pathlib import Path
from shorts_studio_backend.core.storage_gc import dir_size_bytes, cleanup_trash

root = Path("/tmp/shorts_gc_test")
trash = root / "trash"
trash.mkdir(parents=True, exist_ok=True)

f = trash / "a.bin"
f.write_bytes(b"x" * 100)

print("SIZE_BEFORE", dir_size_bytes(str(root)))
removed = cleanup_trash(str(trash), ttl_hours=999999)
print("REMOVED_NOW", removed)
print("SIZE_AFTER", dir_size_bytes(str(root)))
