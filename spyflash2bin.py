#!/usr/bin/env python

import sys
import csv
import struct

class DataDoneException(Exception):
    pass

class SPIData(object):
    def __init__(self, MOSI=0, MISO=0):
        self.MOSI = int(MOSI, 16)
        self.MISO = int(MISO, 16)

class SalaeSPIFlash2BinCSV(object):

    MOSI = 2
    MISO = 3

    def __init__(self, csvfile):
        self.csv = []
        self.csv_index = 0
        self._build_byte_list(csvfile)

    def _build_byte_list(self, csvfile):
        with open(csvfile, 'r') as fp:
            sys.stdout.write("Crunching CSV data...\n")

            for row in csv.reader(fp):
                try:
                    self.csv.append(SPIData(MOSI=row[self.MOSI], MISO=row[self.MISO]))
                except ValueError:
                    pass

    def _next(self, peek=False):
        try:
            entry = self.csv[self.csv_index]
        except IndexError as e:
            raise DataDoneException

        if not peek:
            self.csv_index += 1

        return entry

    def _SPI_ADDRESS(self):
        address  = (self._next().MOSI << (8*2))
        address |= (self._next().MOSI << (8*1))
        address |=  self._next().MOSI
        return address

    def _SPI_READ(self, dummy=False):
        data = ''
        address = self._SPI_ADDRESS()

        if dummy:
            dummy = self._next()

        while self._next(peek=True).MOSI == 0x00:
            data += chr(self._next().MISO)

        return (address, data)

    def _build_mem_map(self, flash):
        data = ''
        last_size = 0
        last_address = 0

        sys.stdout.write("Re-building SPI flash memory layout...\n")

        addresses = list(flash.keys())
        addresses.sort()

        for address in addresses:
            expected_address = last_address + last_size
            missing_size = address - expected_address

            if missing_size > 0:
                data += "\xFF" * missing_size
                sys.stdout.write("Missing %d bytes of data between 0x%X and 0x%X!\n" % (missing_size, expected_address, address))

            data += flash[address]

            last_address = address
            last_size = len(flash[address])

        return data

    def _read(self):
        flash = {}

        sys.stdout.write("Searching SPI data for read commands...\n")

        try:
            while True:
                cmd = self._next().MOSI

                if cmd == 0x03:
                    (address, data) = self._SPI_READ()
                elif cmd == 0x0B:
                    (address, data) = self._SPI_READ(dummy=True)
                else:
                    data = None
                    address = None

                if address is not None:
                    flash[address] = data
        except DataDoneException:
            pass

        return flash

    def read(self):
        flash = self._read()
        data  = self._build_mem_map(flash)
        return data

if __name__ == "__main__":
    try:
        infile = sys.argv[1]
        outfile = sys.argv[2]
    except IndexError:
        sys.stderr.write("Usage: %s <input CSV file> <output binary file>\n" % sys.argv[0])
        sys.exit(1)

    fp = open(outfile, 'wb')
    data = SalaeSPIFlash2BinCSV(infile).read()
    try:
        data = bytes(data, 'latin-1')
    except:
        pass
    fp.write(data)
    fp.close()

