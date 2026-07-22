import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000

def main():
    threading.Timer(1.0, webbrowser.open, args=(f"http://{HOST}:{PORT}",)).start()
    uvicorn.run("server.app:app", host=HOST, port=PORT)

if __name__ == "__main__":
    main()
