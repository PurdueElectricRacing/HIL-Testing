# HIL Tester for PER

## Running

- Code in `./TestBench` runs on the Arduino
	- Basically it just reads commands over the serial port and either executs them or writes messages back over the serial port
	- To flash it, use the Arduino IDE
- Code in `./Scripts` runs on your laptop
	- It uses all the Python files
	- Each file in `./Scripts` can run a Pytest script to test some board on the car
	- Do `./test.sh [filename]` to run the script, or no filename to run all of them. 