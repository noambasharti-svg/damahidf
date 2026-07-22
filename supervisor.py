import subprocess
import time
import sys
import os
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))

def check_app_health():
    try:
        res = urllib.request.urlopen('http://127.0.0.1:5001/api/units', timeout=3)
        return res.status == 200
    except Exception:
        return False

def run_supervisor():
    print("==========================================")
    print("    IDF ATTENDANCE SYSTEM SUPERVISOR     ")
    print("==========================================")
    
    app_proc = None
    tunnel_proc = None
    
    while True:
        try:
            # Check/Start App Server (Waitress)
            if app_proc is None or app_proc.poll() is not None:
                print("[SUPERVISOR] Starting Waitress App Server...")
                app_proc = subprocess.Popen([sys.executable, 'app.py'], cwd=APP_DIR)
                time.sleep(2)
                
            # Check/Start Tunnel Daemon (Cloudflare)
            if tunnel_proc is None or tunnel_proc.poll() is not None:
                print("[SUPERVISOR] Starting Cloudflare Tunnel Daemon...")
                tunnel_proc = subprocess.Popen([sys.executable, 'run_tunnel.py'], cwd=APP_DIR)
                time.sleep(2)
                
            # Health check ping
            if not check_app_health():
                print("[SUPERVISOR] App health check failed. Restarting App Server...")
                if app_proc and app_proc.poll() is None:
                    app_proc.terminate()
                app_proc = subprocess.Popen([sys.executable, 'app.py'], cwd=APP_DIR)
                
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n[SUPERVISOR] Stopping all processes...")
            if app_proc and app_proc.poll() is None:
                app_proc.terminate()
            if tunnel_proc and tunnel_proc.poll() is None:
                tunnel_proc.terminate()
            break
        except Exception as e:
            print(f"[SUPERVISOR] Error: {e}")
            time.sleep(3)

if __name__ == '__main__':
    run_supervisor()
