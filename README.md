# HIL Tester for PER

## Running

- Code in `./TestBench` runs on the Arduino
	- Basically it just reads commands over the serial port and either executs them or writes messages back over the serial port
	- To flash it, use the Arduino IDE
- Code in `./scripts` runs on your laptop
	- It uses all the Python files
	- Each file in `./scripts` can run a Pytest script to test some board on the car
- Make sure you correctly set `firmware_path` in `./hil_params.json` to the path of the primary PER firmware repo!

## Notes

### Input vs Output

- `AI`/`DI` = inputs to hil (reads from the car/other board -> Arduino -> laptop/Python)
- `AO`/`DO` = outputs from hil (writes from laptop/Python -> Arduino -> car/other board)