# HIL Tester for PER

## Running

- Code in `./TestBench` runs on the Arduino
	- Basically it just reads commands over the serial port and either executs them or writes messages back over the serial port
	- To flash it, use the Arduino IDE
- Code in `./scripts` starts the Python code that runs on your laptop
	- It uses all the Python files
	- Each file in `./scripts` can run a Pytest script to test some board or signal set on the car
- Make sure you correctly set `firmware_path` in `./hil_params.json` to the path of the primary PER firmware repo!

## Python ibraries

- `pyserial` for serial communication
- `pytest` (and `pytest-check`) for testing
- `python-can`, `cantools`, and `gs_usb` for CAN communication
- `numpy` for data types
- `jsonschema` for validating JSON files

## Notes

### Input vs Output

- `AI`/`DI` = inputs to hil (reads from the car/other board -> Arduino -> laptop/Python)
- `AO`/`DO` = outputs from hil (writes from laptop/Python -> Arduino -> car/other board)