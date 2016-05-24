# CC2531

This directory contains software to be run on a CC2531 USB dongle as provided
with the Texas Instruments CC2530 ZigBee Development Kit. We use the CC2531
for RSSI measurements.

## Compiling

Compile `cc-tool` from source:

    $ git clone https://github.com/dashesy/cc-tool
    $ cd cc-tool
    $ ./configure
    $ make

Compile and flash `cc2531.hex` onto the CC2531 devices using the SmartRF05
evaluation board:

    $ cd src
    $ make
    $ sudo ./../../../cc-tool/cc-tool -ew cc2531.hex -v

## References

This software is based on code from the following sources. Note that the libraries
in this framework are not the full libraries as present on the following links,
but have instead been stripped and edited for our purposes.

- Radio tomography toolchain: https://github.com/timvandermeij/radio-tomography
- multi-Spin 2.0: https://sites.google.com/site/boccamaurizio/home/software-data
- Texas Instruments CC USB library: http://www.ti.com/lit/zip/swrc088
