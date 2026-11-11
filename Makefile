# Tool rules adapted from cpm-plus-juku (BSD-2-Clause; third_party/JUKU-LICENSE).
PYTHON ?= python3
CC ?= cc
CXX ?= c++
BISON ?= bison
AUTOMAKE ?= automake
BUILD := build
OUT := out
BIN := $(BUILD)/bin
ZMAC := $(BIN)/zmac
ZXCC := $(BIN)/zxcc
ZXCC_ARCHIVE := third_party/zxcc/releases/zxcc-0.5.7.tar.gz
ZXCC_SOURCE := $(BUILD)/zxcc-0.5.7
ZXCC_PREFIX := $(BUILD)/zxcc-install
.DEFAULT_GOAL := all
DAC ?= ../dac-emulation
all: build/manifest.json
build/cpm3.sys: src/cpm3-bios.asm tools/regenerate_cpm3.py third_party/cpm3/bdos3.spr third_party/cpm3/scb.asm third_party/cpm3/releases/cpm3bin_unix-20260607.zip third_party/inputs.json $(ZXCC)
	$(PYTHON) tools/regenerate_cpm3.py --adapter-address 0xc000 --top-page 0xbf --metadata-policy gencpm --output $@
build/system.inc: build/cpm3.sys tools/system_contract.py
	$(PYTHON) tools/system_contract.py
build/platform.cim: src/platform.asm src/serial-platform.asm src/serial-common.asm src/console.asm src/keyboard.asm build/system.inc $(wildcard third_party/juku-common/platform/*.asm) third_party/juku-common/platform/rom-abi.inc $(ZMAC)
	$(ZMAC) --zmac -o $@ -o build/platform.lst $<
build/boot-stage.cim: src/boot-stage.asm src/rom-version.asm src/console.asm $(ZMAC)
	$(ZMAC) --zmac -o $@ -o build/boot-stage.lst $<
build/boot.rom: src/boot.asm build/boot-stage.cim $(ZMAC)
	$(ZMAC) --zmac -o build/boot.cim -o build/boot.lst $<
	cp build/boot.cim $@
out/kaypro.img: build/platform.cim build/keys-test.cim build/screen-test.cim tools/build_image.py tools/media.py third_party/cpm3/ccp.com third_party/inputs.json
	$(PYTHON) tools/build_image.py
$(BUILD) $(OUT) $(BIN) $(BUILD)/zmac:
	mkdir -p $@

$(BUILD)/zmac/docgen: third_party/zmac/doc.c | $(BUILD)/zmac
	$(CC) -O2 -DMK_DOC -Wno-main -o $@ $<

$(BUILD)/zmac/doc.inl: $(BUILD)/zmac/docgen third_party/zmac/doc.txt | $(BUILD)/zmac
	cp third_party/zmac/doc.txt $(BUILD)/zmac/doc.txt
	cd $(BUILD)/zmac && ./docgen >/dev/null

# Grouped targets (`&:`) need GNU make 4.3 and macOS ships 3.81, so every
# recipe here that writes more than one file names its command in a variable,
# hangs the dependency off one primary output, and gives each remaining output
# a rule that re-runs the command only if that file went missing on its own.
# The command cannot use $< or $@: it is shared by rules with different ones.
ZMAC_PARSER := $(BISON) --defines=$(BUILD)/zmac/parser.h \
	--output=$(BUILD)/zmac/parser.c third_party/zmac/zmac.y

$(BUILD)/zmac/parser.c: third_party/zmac/zmac.y | $(BUILD)/zmac
	$(ZMAC_PARSER)

$(BUILD)/zmac/parser.h: $(BUILD)/zmac/parser.c
	@test -f $@ || $(ZMAC_PARSER)

$(BUILD)/zmac/parser.o: $(BUILD)/zmac/parser.c $(BUILD)/zmac/parser.h \
		$(BUILD)/zmac/doc.inl third_party/zmac/mio.h
	$(CC) -O2 -c -I$(BUILD)/zmac -Ithird_party/zmac -o $@ $<

$(BUILD)/zmac/doc.o: third_party/zmac/doc.c $(BUILD)/zmac/doc.inl \
		$(BUILD)/zmac/parser.h
	$(CC) -O2 -c -I$(BUILD)/zmac -Ithird_party/zmac -o $@ $<

$(BUILD)/zmac/mio.o: third_party/zmac/mio.c $(BUILD)/zmac/parser.h \
		$(BUILD)/zmac/doc.inl
	$(CC) -O2 -c -I$(BUILD)/zmac -Ithird_party/zmac -o $@ $<

$(BUILD)/zmac/zi80dis.o: third_party/zmac/zi80dis.cpp \
		third_party/zmac/zi80dis.h $(BUILD)/zmac/parser.h
	$(CXX) -O2 -Wno-unused-result -c -I$(BUILD)/zmac \
		-Ithird_party/zmac -o $@ $<

$(ZMAC): $(BUILD)/zmac/parser.o $(BUILD)/zmac/doc.o \
		$(BUILD)/zmac/mio.o $(BUILD)/zmac/zi80dis.o | $(BIN)
	$(CXX) -o $@ $^

$(ZXCC): $(ZXCC_ARCHIVE) | $(BUILD) $(BIN)
	test "$$(sha256sum $< | cut -d' ' -f1)" = \
		6095119a31a610de84ff8f049d17421dd912c6fd2df18373e5f0a3bc796eb4bf
	mkdir -p $(ZXCC_SOURCE) $(ZXCC_PREFIX)
	tar -xzf $< --strip-components=1 -C $(ZXCC_SOURCE)
	for confdir in config cpmio/config cpmredir/config; do cp "$$($(AUTOMAKE) --print-libdir)/config.guess" "$$($(AUTOMAKE) --print-libdir)/config.sub" "$(ZXCC_SOURCE)/$$confdir/"; done
	cd $(ZXCC_SOURCE) && CFLAGS='-O2 -std=gnu17' \
		./configure --prefix=$(abspath $(ZXCC_PREFIX))
	$(MAKE) -C $(ZXCC_SOURCE)
	$(MAKE) -C $(ZXCC_SOURCE) install
	cp $(ZXCC_PREFIX)/bin/zxcc $@



probe: build/kaypro-probe
build/kaypro-probe: tools/probe.c $(DAC)/machines/kaypro2/kaypro2.c $(DAC)/machines/kaypro2/kaypro2.h $(DAC)/common/cpu/z80.c $(DAC)/common/cpu/z80.h $(DAC)/common/trace/trace.c $(DAC)/common/trace/trace.h $(DAC)/third_party/cpu/chips/z80.h | build
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -I$(DAC) tools/probe.c $(DAC)/machines/kaypro2/kaypro2.c $(DAC)/common/cpu/z80.c $(DAC)/common/trace/trace.c -o $@

SHLIB_EXT := $(if $(filter Darwin,$(shell uname)),dylib,so)
board-test: build/board-test.$(SHLIB_EXT)
build/board-test.$(SHLIB_EXT): tools/board_test.c $(DAC)/machines/kaypro2/kaypro2.c $(DAC)/machines/kaypro2/kaypro2.h $(DAC)/common/cpu/z80.c $(DAC)/common/cpu/z80.h $(DAC)/common/trace/trace.c $(DAC)/common/trace/trace.h $(DAC)/third_party/cpu/chips/z80.h | build
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -shared -fPIC -I$(DAC) tools/board_test.c $(DAC)/machines/kaypro2/kaypro2.c $(DAC)/common/cpu/z80.c $(DAC)/common/trace/trace.c -o $@

build/keys-test.cim: src/keys-test.asm $(ZMAC)
	$(ZMAC) --zmac -o $@ $<
build/manifest.json: out/kaypro.img build/boot.rom tools/build_contract.py
	$(PYTHON) tools/build_contract.py
.PHONY: all probe board-test

build/screen-test.cim: src/screen-test.asm $(ZMAC)
	$(ZMAC) --zmac -o $@ $<
