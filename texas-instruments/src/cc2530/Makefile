# Applications and paths
SDCC = sdcc
SDCC_LIB = /usr/share/sdcc/lib
PACKIHX = packihx

# Include paths, object definitions and compilation flags
ROOT = $(realpath .)
CC_USB_ROOT = $(ROOT)/../../lib/cc-usb-firmware
MULTI_SPIN_ROOT = $(ROOT)/../../lib/multi-spin-3.0
INCLUDES =	-I$(MULTI_SPIN_ROOT) \
			-I$(CC_USB_ROOT)/common \
			-I$(CC_USB_ROOT)/common/cc8051 \
			-I$(CC_USB_ROOT)/radios/cc2530 \
			-I$(CC_USB_ROOT)/targets/interface \
			-I$(CC_USB_ROOT)/targets/srf05_soc
OBJS =	$(ROOT)/cc2530.rel \
		$(CC_USB_ROOT)/common/hal_int.rel \
		$(CC_USB_ROOT)/radios/cc2530/clock.rel \
		$(CC_USB_ROOT)/radios/cc2530/hal_mcu.rel \
		$(CC_USB_ROOT)/targets/srf05_soc/hal_assert.rel \
		$(CC_USB_ROOT)/targets/srf05_soc/hal_board.rel \
		$(CC_USB_ROOT)/targets/srf05_soc/hal_led.rel \
		$(MULTI_SPIN_ROOT)/leds.rel \
		$(MULTI_SPIN_ROOT)/rf.rel
WARNINGS = --Werror
HARDWARE = -Dchip=2530 --model-large
CODE = -DNDEBUG --opt-code-size
CFLAGS += $(INCLUDES) $(WARNINGS) $(HARDWARE) $(CODE)

# Targets
all: cc2530

cc2530: $(OBJS)
	$(SDCC) $(CFLAGS) -L $(SDCC_LIB)/large -o $@.ihx $(OBJS)
	$(PACKIHX) $@.ihx > $@.hex

%.rel: %.c
	$(SDCC) -c $(CFLAGS) $< -o $@

clean:
	rm -f $(OBJS) $(OBJS:.rel=.asm) $(OBJS:.rel=.lst) $(OBJS:.rel=.rst) $(OBJS:.rel=.sym) *.hex *.ihx *.lk *.map *.mem
