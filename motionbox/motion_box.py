#!/usr/bin/env python3
"""Motion Box - start here:  python3 motion_box.py   (add --quick to skip splash and start window)"""
import os
import socket
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mb_core  # noqa: E402
from mb_app import App  # noqa: E402

PORT = 47831


def single_instance():
    """Only one Motion Box at a time: a second launch just brings the first window to the front."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.bind(("127.0.0.1", PORT))
        srv.listen(2)
    except OSError:
        try:                                                    # somebody holds the port: is it Motion Box?
            c = socket.create_connection(("127.0.0.1", PORT), timeout=1.0)
            c.sendall(b"raise")
            c.close()
            return None                                         # yes - it was told to show itself, this copy quits
        except OSError:
            return srv                                          # something else uses the port: just start

    def listen():
        while True:
            try:
                conn, _ = srv.accept()
                conn.recv(16)
                conn.close()
                mb_core.RAISE_REQUEST[0] = True
            except OSError:
                return
    threading.Thread(target=listen, daemon=True).start()
    return srv


def main():
    lock = single_instance()
    if lock is None:
        return
    App(quick="--quick" in sys.argv).run()


if __name__ == "__main__":
    main()
