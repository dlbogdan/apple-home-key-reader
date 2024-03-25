import logging
import os
import socket
from operator import attrgetter

from util.threads import create_runner

log = logging.getLogger()

class IPCService:
    def __init__(
        self,
        sockfile: str = "/dev/shm/homekey-ipc.socket",
    ) -> None:        
        self._run_flag = True
        self._runner = None
        self._sockfile = sockfile
        self._connected: bool = False
        self._conn=None
        self._addr=None
        
    def on_received(self,value):
        """This method will be called when a message is received on the socket"""
        log.info(f"{value}")
        # Currently overwritten by accessory.py
    
    def send(self,value):
        log.info(f"sending {value} to the physical lock {value}")
        strvalue=str(value)+'\n'
        self._write_ipcsocket(strvalue.encode())

        
    def start(self):
        self._socket=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if os.path.exists(self._sockfile):
            os.remove(self._sockfile)
        self._socket.bind(self._sockfile)
        self._socket.listen(0)
        
        self._runner = create_runner(
            name="physlockipc",
            target=self.run,
            flag=attrgetter("_run_flag"),
            delay=0,
            exception_delay=5,
            start=True,
        )
        log.info(f"IPC Service starting on socket file {self._sockfile}")

    def stop(self):
        log.info("Stopping IPC Service")
        self._run_flag = False
        if self._connected:
            self._conn.shutdown(2)    # 0 = done receiving, 1 = done sending, 2 = both
            self._conn.close()
        self._socket.shutdown(2)
        self._socket.close()
        
        if os.path.exists(self._sockfile):
            os.remove(self._sockfile)

        if self._runner is not None:
              self._runner.join()

            
    def _write_ipcsocket(self,data):
        if self._connected:
            self._conn.send(data)
        else:
            log.error('Client (physical lock driver) not connected to socket!')
        
    def _read_ipcsocket(self):
            if self._run_flag:
                ipcdata=self._conn.recv(1024)
            if not ipcdata:
                log.error('Connection closed')    
                self._connected=False
            else:
                #TODO: validate data received
                try:
                    self.on_received(int(ipcdata))
                except ValueError:
                    log.info(f"Received invalid data {ipcdata}")

    def run(self):      
        while self._run_flag:
            if not self._connected:
                log.info("Waiting for Physical Lock IPC Driver to connect...")
                self._conn=None
                self._addr=None
                try:
                    self._conn, self._addr = self._socket.accept()
                except OSError:
                    log.error("Socket destroyed while accepting connection")
                    
                if not self._conn is None:
                    log.info(f"Connection accepted {self._conn}, {self._addr}")
                else:
                    log.error(f"Socket failure")
                    
                self._connected=True
            else:
                self._read_ipcsocket()

    def get_configuration_state(self):
        log.info("get_configuration_state")
        return 0
