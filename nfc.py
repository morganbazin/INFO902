import nxppy

mifare = nxppy.Mifare()

print("Scan your NFC badge...")

try:
    while True:
        try:
            uid = mifare.select()
            print(f"Badge UID: {uid}")
        except nxppy.SelectError:
            pass  # No card detected

except KeyboardInterrupt:
    print("\nExiting...")
