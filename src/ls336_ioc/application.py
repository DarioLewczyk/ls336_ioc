import asyncio
import logging
import argparse

from caproto.asyncio.server import start_server
from .ioc import LakeShoreIoc
from .config import DEFAULT_HOST, DEFAULT_PREFIX, DEFAULT_PORT


def main():
    parser = argparse.ArgumentParser(description="Lakeshore 336 EPICS IOC")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--visa", default="@py")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    dev = f"TCPIP::{args.host}::{args.port}::SOCKET"

    ioc = LakeShoreIoc(prefix=args.prefix, dev=dev, rman=args.visa)

    async def run():
        logging.info("Starting IOC, PV list following")
        for pv in ioc.pvdb:
            logging.info(f"  {pv}")
        await start_server(ioc.pvdb)

    asyncio.run(run())

