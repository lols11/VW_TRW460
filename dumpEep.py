#!/usr/bin/env python3
import argparse
import can
import isotp
import time
from tqdm import tqdm


def parse_args():
    parser = argparse.ArgumentParser(
        description='Dump eeprom via UDS 0x23 over ISO-TP'
    )
    parser.add_argument(
        '-d', '--dump',
        metavar='FILE',
        help='dump 6 bytes of response skipping the first byte (resp code) to binary file'
    )
    return parser.parse_args()


def setup_can():
    bus = can.Bus(
        interface='socketcan',  
        channel='can0',
        bitrate=500000
    )
    address = isotp.Address(
        addressing_mode=isotp.AddressingMode.Normal_11bits,
        txid=0x713,  # TX ID  (tester → ECU)
        rxid=0x77D   # RX ID odbioru  (ECU → tester)
    )
    stack = isotp.CanStack(
        bus=bus,
        address=address,
        params={'tx_padding': 0x55}  # padding (ISOTP)
    )
    return stack


def scan_memory(stack, dump_file=None):

    start_addr = 0x800000
    end_addr = 0x801FFF
    step = 6
    for addr in tqdm(
        range(start_addr, end_addr + 1, step),
        desc="dumping memory",
        unit=f"addr/{step}"
    ):
        # (0x23, ALFID=0x13)
        payload = bytes([0x23, 0x13]) + addr.to_bytes(3, 'big') + bytes([0x06])
        stack.send(payload)

        # timeout (0.6 s)
        deadline = time.time() + 0.6
        resp = None
        while time.time() < deadline:
            stack.process()
            if stack.available():
                resp = stack.recv()
                break
            time.sleep(0.015)

        if resp is None:
            continue

        # Negative response 0x31: Request Out Of Range
        if resp[0] == 0x7F and resp[1] == 0x23 and resp[2] == 0x31:
            continue

        # print
        if resp[0] == 0x7F:
            nrc = resp[2]
            tqdm.write(f"Address 0x{addr:06X}: NRC=0x{nrc:02X}")
        else:
            tqdm.write(f"Address 0x{addr:06X}: RESP={resp.hex()}")

        # Dump 
        if dump_file:
            # resp[1:7] gives bytes 1 to 6
            dump_file.write(resp[1:7])


def main():
    args = parse_args()
    stack = setup_can()

    if args.dump:
        with open(args.dump, 'wb') as dump_file:
            scan_memory(stack, dump_file)
    else:
        scan_memory(stack)


if __name__ == '__main__':
    main()
