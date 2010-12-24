import struct

format = "!i"

request_update = struct.pack(format, 0)
update_complete = struct.pack(format, 1)

