CC = g++
CFLAGS = -g -Wall
CFLAGS += -Isrc -Ilib/cimg

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
