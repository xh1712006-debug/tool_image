import urllib.request
import zipfile
import os

SCRCPY_URL = "https://github.com/Genymobile/scrcpy/releases/download/v2.4/scrcpy-win64-v2.4.zip"
SCRCPY_ZIP = "scrcpy.zip"
EXTRACT_DIR = "scrcpy"

def setup_scrcpy():
    if os.path.exists(os.path.join(EXTRACT_DIR, "scrcpy.exe")):
        print("[+] SCRCPY is already installed!")
        return True
        
    print(f"[*] Downloading SCRCPY from {SCRCPY_URL}...")
    try:
        urllib.request.urlretrieve(SCRCPY_URL, SCRCPY_ZIP)
        print("[+] Download successful! Extracting...")
        
        with zipfile.ZipFile(SCRCPY_ZIP, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)
            
        print("[+] Extraction successful!")
        
        if os.path.exists(SCRCPY_ZIP):
            os.remove(SCRCPY_ZIP)
        return True
    except Exception as e:
        print(f"[-] Error downloading SCRCPY: {e}")
        return False

if __name__ == "__main__":
    setup_scrcpy()
