import os
import time
import subprocess
import requests
import sys
import zipfile
import signal
import json

# Configuration
APP_PATH = '/mnt/d/app.py'
# Use the sample resume file we identified
TEST_FILE = '/mnt/d/CV_060205_Papa_Samba_Diop_RP_IngénieurDeDonnées_2025-09_FR.docx'
SERVER_URL = 'http://localhost:5000'
UPLOAD_URL = f'{SERVER_URL}/upload'
DOWNLOAD_PATH = '/mnt/d/test_output.docx'

def wait_for_server(url, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(url)
            return True
        except requests.ConnectionError:
            time.sleep(0.5)
            pass
    return False

def run_test():
    print(f"Starting E2E Test...")
    
    # Check if test file exists
    if not os.path.exists(TEST_FILE):
        print(f"❌ Test file not found: {TEST_FILE}")
        return False

    # 1. Start the Flask Server
    print("Starting Flask server...")
    # Use venv if available
    if os.path.exists('/mnt/d/venv/bin/python3'):
        python_cmd = '/mnt/d/venv/bin/python3'
    else:
        python_cmd = 'python3'
        
    print(f"Using python: {python_cmd}")
    
    # Start server in new process group so we can verify output and kill it cleanly
    server_process = subprocess.Popen(
        [python_cmd, APP_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd='/mnt/d', # IMPORTANT: Set working directory
        preexec_fn=os.setsid
    )
    
    try:
        # 2. Wait for server to be ready
        if not wait_for_server(SERVER_URL):
            print("❌ Server failed to start within timeout!")
            # Print output if failed
            try:
                outs, errs = server_process.communicate(timeout=1)
                print(f"STDOUT: {outs.decode()}")
                print(f"STDERR: {errs.decode()}")
            except:
                pass
            return False
            
        print("✅ Server started successfully")
        
        # 3. Upload File
        print(f"Uploading file: {os.path.basename(TEST_FILE)}...")
        with open(TEST_FILE, 'rb') as f:
            files = {'file': f}
            response = requests.post(UPLOAD_URL, files=files)
        
        if response.status_code != 200:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        data = response.json()
        print(f"Response JSON: {json.dumps(data, indent=2)}")
        
        # 4. Validate Response Structure
        if not data.get('success'):
            print("❌ API reported failure")
            return False
            
        download_url = data.get('download_url')
        filename = data.get('filename')
        
        if not download_url:
            print("❌ No download_url in response")
            return False
            
        if not filename.endswith('.docx'):
            print(f"❌ Expected filename ending in .docx, got: {filename}")
            return False
            
        print(f"✅ Upload successful. Download URL: {download_url}")
        
        # 5. Download Result
        full_download_url = f"{SERVER_URL}{download_url}"
        print(f"Downloading from {full_download_url}...")
        download_response = requests.get(full_download_url)
        
        if download_response.status_code != 200:
            print(f"❌ Download failed with status {download_response.status_code}")
            return False
            
        # 6. Save and Verify Content
        with open(DOWNLOAD_PATH, 'wb') as f:
            f.write(download_response.content)
            
        print(f"✅ File downloaded to {DOWNLOAD_PATH}")
        
        # Check if valid DOCX (it's a ZIP archive)
        try:
            with zipfile.ZipFile(DOWNLOAD_PATH, 'r') as z:
                # Check for word/document.xml which is standard in DOCX
                if 'word/document.xml' in z.namelist():
                    print("✅ Valid DOCX structure verified (contains word/document.xml)")
                else:
                    print("❌ Invalid DOCX: Missing word/document.xml")
                    return False
        except zipfile.BadZipFile:
            print("❌ Downloaded file is not a valid ZIP archive (corrupted DOCX)")
            return False
        except Exception as e:
            print(f"❌ Error validating DOCX: {e}")
            return False
            
        print("\n🎉 E2E TEST PASSED SUCCESSFULLY! The PDF removal was verified since we received a direct DOCX file.")
        return True
        
    except Exception as e:
        print(f"❌ Test Failed with Exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup server
        print("Stopping server...")
        try:
            os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
            server_process.wait(timeout=5)
        except:
            try:
                server_process.terminate()
            except:
                pass
        print("Test complete.")

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
