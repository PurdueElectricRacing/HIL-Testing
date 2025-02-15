
/*
    Microchip 63 taps Single Digital Potentiometer
    Simple two-wire UP/DOWN interface
    Author: dzalf - Daniel Melendrez
    Date: June 2020 (COVID-19 Vibes)
    Version: 1.1.1  - Initial deployment
             1.1.2  - General cleanup. Implemented new and overloaded methods that allow
                    to select the desired tap. It is now possible to select the nominal 
                    resistance value or override it by setting the measured value

*/

#ifndef MCP4021_h
#define MCP4021_h

#include "Arduino.h"

#define MCP4021_TAP_NUMBER 63                // Total taps, 63 resistors. Wiper values are from 0x00 to 0x3F
#define MCP4021_DEFAULT_TAP_COUNT 63         // Half way resistance
#define MCP4021_NOMINAL_RESISTANCE 2100      // MCP4021
#define MCP4021_WIPER_RESISTANCE 75          // 75 typical (According to datasheet)

class MCP4021 {

  public:

    // Constructors:
    MCP4021(uint8_t cs, uint8_t ud);
    MCP4021(uint8_t cs, uint8_t ud, bool dbg);
    
    // Methods:

    // Setup the device's connections
    void setup(void);
    // Begin the digital potentiometer using a nominal resistance of 100 kOhms
    void begin(void);
    // Begin the digital potentiometer with a custom value. Overloaded method.
    void begin(float);
    // Retrieve the currently set tap
    int taps(void);
    // Retrieve the fractional position of the wiper
    float wiper(void);
    // Issue a single tap increment command
    void inc(void);
    // Issue a single tap decrement command
    void dec(void);
    // Set the wiper position to the minimum
    void zeroWiper(void);
    // Set the wiper position to the maximum
    void maxWiper(void);
    // Retrieve a mathematical approximation of the current resistance value
    float readValue(void);
    // Set the closest possible resistance value -> mathematical approximation
    uint8_t setValue(float);
    // Set the tap to a desired position within its nominal range
    uint8_t setTap(uint8_t);
    // Read the time it took for increasing the tap
    unsigned long incMicros(void);
    // Read the time it took for decreasing the tap
    unsigned long decMicros(void);
    // Read the time it took for setting the tap
    unsigned long setMicros(void);

  private:

    uint8_t _tapPointer;
    float _nominalResistance;

  protected:

    uint8_t _CSPin;
    uint8_t _UDPin;
    unsigned long _incDelay;
    unsigned long _decDelay;
    unsigned long _setDelay;
    bool _debug;

};

#endif
