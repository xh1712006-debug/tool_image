import urllib.request
import zipfile
import os

ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
ADB_ZIP_PATH = "platform-tools.zip"
EXTRACT_DIR = "adb"

def download_and_extract_adb():
    if os.path.exists(os.path.join(EXTRACT_DIR, "platform-tools", "adb.exe")):
        print("[+] ADB is already installed in adb/platform-tools/adb.exe")
        return True

    print(f"[*] Downloading Android Platform Tools from {ADB_URL}...")
    try:
        urllib.request.urlretrieve(ADB_URL, ADB_ZIP_PATH)
        print("[+] Download successful! Extracting...")
        
        with zipfile.ZipFile(ADB_ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)
            
        print("[+] Extraction successful!")
        
        if os.path.exists(ADB_ZIP_PATH):
            os.remove(ADB_ZIP_PATH)
            
        return True
    except Exception as e:
        print(f"[-] Error during ADB download/extraction: {e}")
        return False

if __name__ == "__main__":
    download_and_extract_adb()
