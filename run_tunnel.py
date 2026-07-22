import subprocess
import time
import re
import qrcode
import os

def start_tunnel():
    print("Starting Cloudflare Tunnel daemon...")
    cloudflared_bin = os.path.join(os.path.dirname(__file__), 'cloudflared')
    
    while True:
        try:
            proc = subprocess.Popen(
                [cloudflared_bin, 'tunnel', '--url', 'http://localhost:5001'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in proc.stdout:
                line_str = line.strip()
                if line_str:
                    print(line_str)
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line_str)
                    if match:
                        current_url = match.group(0)
                        print("\n==========================================")
                        print(f"CLOUDFLARE PUBLIC URL IS LIVE: {current_url}")
                        print("==========================================\n")
                        
                        # Save URL to file
                        with open('public_url.txt', 'w') as f:
                            f.write(current_url)
                            
                        # Generate QR Code image
                        qr = qrcode.QRCode(box_size=10, border=4)
                        qr.add_data(current_url)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        
                        art_dir = '/Users/michaelfilippov/.gemini/antigravity/brain/28ce193c-0150-494c-8a4e-a4951a3a9b84'
                        os.makedirs(art_dir, exist_ok=True)
                        img.save(os.path.join(art_dir, 'public_qr_code.png'))
                        img.save('public_qr_code.png')
            
            proc.wait()
        except Exception as e:
            print(f"Tunnel error: {e}")
        
        print("Tunnel connection closed. Reconnecting in 3 seconds...")
        time.sleep(3)

if __name__ == '__main__':
    start_tunnel()
