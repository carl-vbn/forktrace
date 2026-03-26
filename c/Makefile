CC = gcc
CFLAGS = -g -Wall -Wextra -pedantic
LDFLAGS = -ldl

TARGET = libforktrace.so

all: $(TARGET)

$(TARGET): hook.c
	$(CC) -shared -fPIC -o $@ $< $(LDFLAGS)

.PHONY: all clean

clean:
	rm -f $(TARGET)
