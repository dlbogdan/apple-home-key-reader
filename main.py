import json
import logging
import signal
import sys

from pyhap.accessory_driver import AccessoryDriver

from accessory import Lock
from util.bfclf import BroadcastFrameContactlessFrontend
from repository import Repository
from service import Service
from ipcservice import IPCService

# By default, this file is located in the same folder as the project
CONFIGURATION_FILE_PATH = "configuration.json"


def load_configuration(path=CONFIGURATION_FILE_PATH) -> dict:
    return json.load(open(path, "r+"))


def configure_logging(config: dict):
    log = logging.getLogger()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)8s] %(module)-18s:%(lineno)-4d %(message)s"
    )
    hdlr = logging.StreamHandler(sys.stdout)
    log.setLevel(config.get("level", logging.INFO))
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)
    return log


def configure_hap_accessory(config: dict, homekey_service=None, ipc_service=None):
    driver = AccessoryDriver(
        port=config["port"], persist_file=config["persist"])
    accessory = Lock(
        driver,
        "NFC Lock",
        service=homekey_service,
        ipcservice=ipc_service,
        lock_state_at_startup=int(config.get("default") != "unlocked")
    )
    driver.add_accessory(accessory=accessory)
    return driver, accessory


def configure_nfc_device(config: dict):
    clf = BroadcastFrameContactlessFrontend(
        path=f"tty:{config['port']}:{config['driver']}",
        broadcast_enabled=config.get("broadcast", True),
    )
    return clf


def configure_lock_ipc(config: dict):
    ipcservice = IPCService(
        sockfile=config.get("socketfile"),
    )
    return ipcservice


def configure_homekey_service(config: dict, nfc_device, repository=None):
    service = Service(
        nfc_device,
        repository=repository or Repository(config["persist"]),
        express=config.get("express", True),
        finish=config.get("finish"),
        flow=config.get("flow"),
    )
    return service


def main():
    config = load_configuration()
    log = configure_logging(config["logging"])

    nfc_device = configure_nfc_device(config["nfc"])
    homekey_service = configure_homekey_service(config["homekey"], nfc_device)
    try:
        ipc_service = configure_lock_ipc(config["lock"])
        # ipc_service_enabled = True
    except KeyError:
        log.info("No IPC configured")
        # ipc_service_enabled = False
    hap_driver, _ = configure_hap_accessory(
        config["hap"], homekey_service, ipc_service)

    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(
            s,
            lambda *_: (
                log.info(f"SIGNAL {s}"),
                hap_driver.stop(),
                homekey_service.stop(),
                ipc_service.stop(),
            ),
        )
    # taskmanager.addtask(ipc_service)
    # taskmanager.addtask(homekey_service)
    # taskmanager.addtask(hap_driver)

    # taskmanager.start()
    # hap_driver.start()
    # we need the client, which is the physical lock process driver, to be connected before continuing.
    ipc_service.start()
    homekey_service.start()
    hap_driver.start()

    # if ipc_service_enabled:


if __name__ == "__main__":
    main()
