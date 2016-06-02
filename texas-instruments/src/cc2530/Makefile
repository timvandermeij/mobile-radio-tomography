# Applications and paths
SDCC = sdcc
SDCC_LIB = /usr/share/sdcc/lib
PACKIHX = packihx

# Include paths, object definitions and compilation flags
ROOT = $(realpath .)
MULTI_SPIN_ROOT = $(ROOT)/../../lib/multi-spin-3.0
INCLUDES =	-I$(MULTI_SPIN_ROOT)
OBJS =	$(ROOT)/cc2530.rel \
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
