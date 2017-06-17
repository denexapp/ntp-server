import socket as socket_file
from threading import Thread

import bitstring
import time
import sys
import argparse

class Packet:
    leap_second = 0
    version = 4
    mode = 4
    stratum = 10
    reference_timestamp = 0
    originate_timestamp = 0
    recieve_timestamp = 0
    transmit_timestamp = 0

    def __init__(self, bytes=None):
        if bytes:
            data = bitstring.BitArray(bytes)
            leap_indicator = data[0:2].uint
            if leap_indicator == 1:
                self.leap_second = 1
            elif leap_indicator == 2:
                self.leap_second = -1
            self.version = data[2:5].uint
            self.mode = data[5:8].uint
            self.stratum = data[8:16].uint
            self.reference_timestamp = decode_timestamp(data[128:192])
            self.originate_timestamp = decode_timestamp(data[192:256])
            self.recieve_timestamp = decode_timestamp(data[256:320])
            self.transmit_timestamp = decode_timestamp(data[320:384])

    def to_bytes(self):
        leap_indicator = 0
        if self.leap_second == 1:
            leap_indicator = 1
        elif self.leap_second == -1:
            leap_indicator = 2
        leap_indicator = convert_to_string_of_bits(leap_indicator, 2)
        version = convert_to_string_of_bits(self.version, 3)
        mode = convert_to_string_of_bits(self.mode, 3)
        stratum = convert_to_string_of_bits(self.stratum, 8)
        poll = "00000000"
        precision = "00000000"
        root_delay = "00000000" * 4
        root_dispersion = "00000000" * 4
        reference_identifier = "00000000" * 4
        reference_timestamp = generate_timestamp(self.reference_timestamp)
        originate_timestamp = generate_timestamp(self.originate_timestamp)
        recieve_timestamp = generate_timestamp(self.recieve_timestamp)
        transmit_timestamp = generate_timestamp(self.transmit_timestamp)

        request = leap_indicator + version + mode + stratum + poll + precision + \
                  root_delay + root_dispersion + reference_identifier + reference_timestamp + \
                  originate_timestamp + recieve_timestamp + transmit_timestamp
        return bitstring.BitArray(bin=request).tobytes()


def convert_to_string_of_bits(number, length):
    line = bitstring.BitArray(uint=number, length=length).bin
    return line


def generate_timestamp(time):
    current_time = time
    seconds_since_1900 = int(current_time // 1) + 25567*24*60*60
    first_part = bitstring.BitArray(uint=seconds_since_1900, length=32)
    ms = current_time % 1
    ms_string = ""
    for x in range(32):
        ms *= 2
        if ms >= 1:
            ms_string += "1"
            ms %= 1
        else:
            ms_string += "0"
    return str(first_part.bin) + ms_string


def decode_timestamp(timestamp):
    result = float(timestamp[0:32].uint)
    for x in range(32):
        if timestamp[x+32]:
            result += 1 / 2 ** (x+1)
    result %= 25567 * 24 * 60 * 60
    return result


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--delay", type=int, help="sets fake time delay")
    parser.add_argument("-p", "--port", type=int, help="sets server's port instead of default 123")

    port = 123
    delay = 0

    args = parser.parse_args()

    if args.port:
        if port < 0 or port >= 65536:
            print("Port should be in this interval: 0 <= port <= 65535")
            sys.exit(0)
        else:
            port = args.port
    if args.delay:
        delay = args.delay
    return port, delay


def accept_data(connection):
    result = b""
    while True:
        part = connection.recv(1024)
        if not part:
            break
        else:
            result += part
    return result


def generate_reply(transmit_timestamp, delay=0):
    reply = Packet()
    # this line has no errors
    reply.originate_timestamp = transmit_timestamp
    server_time = time.time() + delay
    reply.recieve_timestamp = server_time
    reply.transmit_timestamp = server_time
    return reply


def handle_connection(address, data, socket, delay=0):
    request = Packet(data)
    reply = generate_reply(request.transmit_timestamp, delay=delay)
    socket.sendto(reply.to_bytes(), address)


def run_server():
    port, delay = parse_args()
    print("SNTP server started.")
    print("Port: {}".format(port))
    print("Delay: {}".format(delay))
    with socket_file.socket(socket_file.AF_INET, socket_file.SOCK_DGRAM) as socket:
        try:
            socket.bind(('127.0.0.1', port))
        except OSError:
            print("Can't bind to UDP port {}.".format(port))
            return
        while True:
            data, address = socket.recvfrom(65535)
            print("New connection from {}".format(address))
            Thread(handle_connection(address, data, socket, delay))


if __name__ == '__main__':
    run_server()