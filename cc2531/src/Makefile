# Applications and paths
SDCC = sdcc
SDCC_LIB = /usr/share/sdcc/lib
PACKIHX = packihx
SDAS8051 = sdas8051

# Include paths, object definitions and compilation flags
ROOT = $(realpath .)
CC_USB_ROOT = $(ROOT)/../lib/cc-usb-firmware/source/components
MULTI_SPIN_ROOT = $(ROOT)/../lib/multi-spin-3.0
INCLUDES =	-I$(MULTI_SPIN_ROOT) \
			-I$(CC_USB_ROOT)/usb/class_cdc \
			-I$(CC_USB_ROOT)/usb/library \
			-I$(CC_USB_ROOT)/common \
			-I$(CC_USB_ROOT)/common/cc8051 \
			-I$(CC_USB_ROOT)/targets/interface \
			-I$(CC_USB_ROOT)/targets/cc2531_dongle \
			-I$(CC_USB_ROOT)/utils \
			-I$(CC_USB_ROOT)/radios/cc2530
OBJS =	$(ROOT)/cc2531.rel \
		$(CC_USB_ROOT)/targets/common/hal_uart_usb.rel \
		$(CC_USB_ROOT)/common/hal_int.rel \
		$(CC_USB_ROOT)/radios/cc2530/clock.rel \
		$(CC_USB_ROOT)/radios/cc2530/hal_mcu.rel \
		$(CC_USB_ROOT)/targets/cc2531_dongle/hal_assert.rel \
		$(CC_USB_ROOT)/targets/cc2531_dongle/hal_board.rel \
		$(CC_USB_ROOT)/targets/cc2531_dongle/hal_led.rel \
		$(CC_USB_ROOT)/usb/class_cdc/usb_cdc_hooks.rel \
		$(CC_USB_ROOT)/usb/class_cdc/usb_firmware_library_config.rel \
		$(CC_USB_ROOT)/usb/class_cdc/usb_uart.rel \
		$(CC_USB_ROOT)/usb/library/cc2531/usb_interrupt.rel \
		$(CC_USB_ROOT)/usb/library/cc2531/usb_suspend.rel \
		$(CC_USB_ROOT)/usb/library/usb_descriptor_parser.rel \
		$(CC_USB_ROOT)/usb/library/usb_framework.rel \
		$(CC_USB_ROOT)/usb/library/usb_standard_requests.rel \
		$(CC_USB_ROOT)/utils/util_buffer.rel \
		$(MULTI_SPIN_ROOT)/leds.rel \
		$(MULTI_SPIN_ROOT)/rf.rel
USB_DESCRIPTOR = $(CC_USB_ROOT)/usb/class_cdc/usb_cdc_descriptor
WARNINGS = --disable-warning 85 --Werror
HARDWARE = -DBUF_SIZE=192 -DUSB_UART -Dchip=2531 --model-large
CODE = -DNDEBUG --opt-code-size
CFLAGS += $(INCLUDES) $(WARNINGS) $(HARDWARE) $(CODE)

# Targets
all: cc2531

cc2531: $(OBJS)
	$(SDCC) $(CFLAGS) -L $(SDCC_LIB)/large -o $@.ihx $(OBJS)
	$(PACKIHX) $@.ihx > $@.hex

%.rel: %.c
	$(SDCC) -c $(CFLAGS) $< -o $@

%.rel: %.asm
	$(SDAS8051) $(INCLUDES) -x -l -s -o $@ $<

clean:
	rm -f $(OBJS) $(OBJS:.rel=.asm) $(OBJS:.rel=.lst) $(OBJS:.rel=.rst) $(OBJS:.rel=.sym) *.hex *.ihx *.lk *.map *.mem
