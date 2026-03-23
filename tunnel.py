from pyngrok import ngrok
import time
import sys

# Optional: set auth token if needed, or simply let it create a temporary local tunnel
try:
    print("Starting ngrok tunnel on port 8000...", flush=True)
    # Start an HTTPs tunnel on port 8000
    public_url = ngrok.connect(8000, bind_tls=True).public_url
    print(f"Tunnel URL: {public_url}", flush=True)
    
    # Keep the tunnel open
    while True:
        time.sleep(60)
except Exception as e:
    print(f"Error starting tunnel: {e}", flush=True)
    sys.exit(1)
