.EXPORT_ALL_VARIABLES:
.PHONY: all build install clean

VERSION = $(shell git describe --tags --always --dirty 2>/dev/null || echo "1.0+unknown")
PROGS = jiramail jirasmtp jirasync

BINDIR ?= /usr/bin

Q = @
VERBOSE ?= $(V)
ifeq ($(VERBOSE),1)
    Q =
endif

quiet_cmd = $(if $(VERBOSE),$(3),$(Q)printf "  %-04s %s\n" "$(1)" "$(2)"; $(3))
GOBUILD   = $(call quiet_cmd,GO,$@,go build)
CP        = $(call quiet_cmd,COPY,$^,cp -f)
RM        = $(Q)rm -f

GO111MODULE = on

all: build

jiramail: cmd/jiramail/jiramail.go
	$(GOBUILD) -ldflags "-X main.version=$(VERSION)" "./$<"

jirasmtp: cmd/jirasmtp/jirasmtp.go
	$(GOBUILD) -ldflags "-X main.version=$(VERSION)" "./$<"

jirasync: cmd/jirasync/jirasync.go
	$(GOBUILD) -ldflags "-X main.version=$(VERSION)" "./$<"

$(PROGS): Makefile

build: $(PROGS)

install: $(PROGS)
	$(CP) -t "$(BINDIR)" -- $(PROGS)

clean:
	$(RM) -- $(PROGS)
