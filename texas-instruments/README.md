# Texas Instruments

This directory contains software to be run on a CC2530 module and a CC2531
USB dongle as provided with the Texas Instruments CC2530 ZigBee Development
Kit. This hardware is used for packet exchange and RSSI measurements.

## Compiling

Compile `cc-tool` from source:

    $ git clone https://github.com/dashesy/cc-tool
    $ cd cc-tool
    $ ./configure
    $ make

Make sure that `cc-tool` is present in your PATH. If not, use a relative
path to the `cc-tool` executable in the command below.

Compile and flash the software onto the devices using the SmartRF05
evaluation board (example for the CC2530 software):

    $ cd src/cc2530
    $ make
    $ sudo cc-tool -ew cc2530.hex -v

## References

This software is based on code from the following sources. Note that the libraries
in this framework are not the complete libraries as present on the following links.
They have been stripped and edited for our purposes.

- Radio tomography toolchain: https://github.com/timvandermeij/radio-tomography
  (GPL v3 license)
- multi-Spin 2.0: https://sites.google.com/site/boccamaurizio/home/software-data
  (GPL v3 license)
- Texas Instruments CC USB firmware library: http://www.ti.com/lit/zip/swrc088
  (separate license in all files)
