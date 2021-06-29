#!/usr/bin/env python3
import argparse
import binascii
import traceback
from collections import OrderedDict

import yaml

from paradox.connections.ip.parsers import (IPMessageCommand, IPMessageRequest,
                                            IPMessageResponse, IPMessageType,
                                            IPPayloadConnectResponse)
from paradox.hardware import create_panel


class Colors: # You may need to change color settings
    RED = '\033[31m'
    ENDC = '\033[m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    ON_WHITE = '\033[47m'


def ordered_load(stream, Loader=yaml.loader.SafeLoader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    return yaml.load(stream, OrderedLoader)


class PayloadParser:
    def __init__(self):
        self.panel = create_panel(None)

    def parse(self, parsed):
        try:
            message_type = parsed.header.message_type
            if message_type == IPMessageType.serial_passthrough_request:
                self._parse_serial_passthrough_request(parsed)
            elif message_type == IPMessageType.serial_passthrough_response:
                self._parse_serial_passthrough_response(parsed)
            elif message_type == IPMessageType.ip_request:
                self._parse_ip_request(parsed)
            elif message_type == IPMessageType.ip_response:
                self._parse_ip_response(parsed)
        except Exception:
            traceback.print_exc()

    def _parse_ip_response(self, parsed):
        if parsed.header.command == IPMessageCommand.connect:
            print(f"{Colors.ON_WHITE}{IPPayloadConnectResponse.parse(parsed.payload)}{Colors.ENDC}")
        else:
            print(
                f"{Colors.RED}No parser for ip_response payload: {binascii.hexlify(parsed.payload)}{Colors.ENDC}"
            )

    def _parse_serial_passthrough_response(self, parsed):
        parsed_payload = self.panel.parse_message(parsed.payload, direction="frompanel")
        if parsed_payload is not None:
            if parsed_payload is not None:
                print(f"{Colors.ON_WHITE}{parsed_payload}{Colors.ENDC}")
            else:
                print(
                    f"{Colors.RED}No parser for serial_passthrough_response payload: {binascii.hexlify(parsed.payload)}{Colors.ENDC}"
                )

            if parsed_payload.fields.value.po.command == 0:  # panel detection
                self.panel = create_panel(None, parsed_payload)
            if parsed_payload.fields.value.po.command == 5:  # eeprom/ram read
                self._parse_serial_passthrough_eeprom_read(parsed_payload)

    def _parse_serial_passthrough_eeprom_read(self, parsed_payload):
        if (
            "control" in parsed_payload.fields.value
            and parsed_payload.fields.value.control.ram_access
            and parsed_payload.fields.value.control._eeprom_address_bits == 0
            and parsed_payload.fields.value.bus_address == 0
        ):
            ram_address = parsed_payload.fields.value.address
            ram_parser = self.panel.get_message("RAMDataParserMap").get(ram_address)
            if ram_parser is not None:
                print(f"{Colors.ON_WHITE}{ram_parser.parse(parsed_payload.fields.value.data)}{Colors.ENDC}")
            else:
                print(
                    f"{Colors.RED}No parser for {ram_address} ram address, data: {binascii.hexlify(parsed_payload.fields.value.data)}{Colors.ENDC}"
                )

    def _parse_serial_passthrough_request(self, parsed):
        parsed_payload = self.panel.parse_message(parsed.payload)
        if parsed_payload is not None:
            print(f"{Colors.ON_WHITE}{parsed_payload}{Colors.ENDC}")
        else:
            print(
                f"{Colors.RED}No parser for serial_passthrough_request payload: {binascii.hexlify(parsed.payload)}{Colors.ENDC}"
            )

    def _parse_ip_request(self, parsed):
        if parsed.header.command == IPMessageCommand.multicommand:
            i = 0
            while i < len(parsed.payload):
                cmd_len = parsed.payload[i]
                i += 1
                cmd = parsed.payload[i:i+cmd_len]
                assert len(cmd) == cmd_len
                i += cmd_len
                print(f"{Colors.ON_WHITE}{cmd}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}No parser for ip_request payload: {binascii.hexlify(parsed.payload)}{Colors.ENDC}")


def decrypt_file(file, password, max_packets: int = None):
    try:
        data = ordered_load(file, yaml.loader.SafeLoader)
        parser = PayloadParser()

        n = 0
        for key, value in data.items():
            if not value[0] == 0xaa:
                print(f"{Colors.RED}Not an IP packet: {value}{Colors.ENDC}")
                continue
            header = value[0:16]
            payload = value[16:]

            is_request = header[3] in [3, 4]
            print(
                f"{Colors.BLUE}PC->IP: " if is_request else f"{Colors.GREEN}IP->PC:\n",
                f"\theader: {binascii.hexlify(header)}\n",
                f"\tencrypted_payload: {binascii.hexlify(payload)}",
            )

            if is_request:
                parsed = IPMessageRequest.parse(value, password=password)
            else:
                parsed = IPMessageResponse.parse(value, password=password)

            if (
                parsed.header.command == IPMessageCommand.connect
                and parsed.header.message_type == IPMessageType.ip_request
            ):
                if parsed.header.sub_command == 0:
                    assert password == parsed.payload, "Wrong decryption password"
                if parsed.header.sub_command == 3:
                    assert parsed.payload[0] & 240 == 16  # Connection succeeded

            if (
                parsed.header.command == IPMessageCommand.connect
                and parsed.header.message_type == IPMessageType.ip_response
            ):
                password = parsed.payload[1:17]
                assert len(password) == 16, "Wrong password length"

            print(
                f"\tpayload: {binascii.hexlify(parsed.payload)}\n",
                f"\tpayload_raw: {parsed.payload}"
            )

            print(parsed)
            print(Colors.ENDC)
            parser.parse(parsed)

            if not is_request:
                print(
                    "----end %s-------------------------------------------------------------"
                    % key
                )
            n += 1

            if max_packets is not None and n > max_packets:
                print(f"Force stopped on {max_packets} packets")
                return

    except yaml.YAMLError as exc:
        print(f"{Colors.RED}{exc}{Colors.ENDC}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file",
        type=argparse.FileType("r"),
        help="YAML file to parse. In wireshark right click on the first "
        "package, 'Follow->TCP Stream', 'Show and save data as': "
        "'YAML', copy contents to a file.",
    )
    parser.add_argument(
        "password",
        type=str,
        default="paradox",
        help="IP Module password for decryption",
    )
    parser.add_argument(
        "-n",
        "--packets",
        type=int,
        help="Packets to decrypt",
    )

    args = parser.parse_args()

    decrypt_file(args.file, args.password.encode("utf8"), args.packets)


if __name__ == "__main__":
    main()
