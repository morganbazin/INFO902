import time
from pirc522 import RFID

# Initialize RFID reader
rdr = RFID()

print("Scan your NFC badge...")

try:
    while True:
        rdr.wait_for_tag()  # Wait for an NFC tag
        (error, tag_type) = rdr.request()

        if not error:
            print(f"Detected NFC Tag Type: {tag_type}")

            (error, uid) = rdr.anticoll()  # Get tag UID
            if not error:
                uid_str = "-".join(map(str, uid))
                print(f"Badge UID: {uid_str}")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nExiting...")
    rdr.cleanup()
