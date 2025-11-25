CC = g++
CFLAGS = -Wall -O2 -std=c++20 -ffast-math -g
CFLAGS += -Isrc -Iinclude -Ilib/cimg

ifeq ($(OS),Windows_NT)
    CFLAGS += -lgdi32
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Linux)
        CFLAGS += -lm -lpthread -lX11
    endif
    ifeq ($(UNAME_S),Darwin)
        CFLAGS += -lm -lpthread -I/usr/X11R6/include -L/usr/X11R6/lib -lm -lpthread -lX11
    endif
endif


SRC = $(wildcard src/**/*.cpp) $(wildcard src/*.cpp) $(wildcard src/**/**/*.cpp) $(wildcard src/**/**/**/*.cpp)
OBJ = $(SRC:.cpp=.o)
BIN = build

.PHONY: all clean

main: $(OBJ)
	mkdir -p ./$(BIN)
	$(CC) -o $(BIN)/main $^ $(LDFLAGS) $(CFLAGS)

run: main
	$(BIN)/main

%.o: %.cpp
	$(CC) -o $@ -c $< $(CFLAGS)

json: clean
	bear -- make main

clean:
	rm -rf $(BIN) $(OBJ)
