#include "DigiPot.h"
#include <Arduino.h>

static void delay_500ns();

void digipot_init(uint8_t cs_pin, uint8_t ud_pin, digipot_t *dp)
{
    dp->cs_pin = cs_pin;
    dp->ud_pin = ud_pin;
    dp->setpoint = DIGIPOT_INIT;
    pinMode(cs_pin, OUTPUT);
    pinMode(ud_pin, OUTPUT);
    digitalWrite(dp->cs_pin, 1);
}

void digipot_set(uint8_t value, digipot_t *dp)
{
    // Clamp setpoint
    if (value >= DIGIPOT_STEPS) value = DIGIPOT_STEPS - 1;

    // To not write to EEPROM, ud pin must start and
    // end at the same position

    // Increment
    if (value > dp->setpoint)
    {
        digitalWrite(dp->ud_pin, 1); // Increment mode
        delay_500ns();
        digitalWrite(dp->cs_pin, 0); // Select device
        while (value != dp->setpoint)
        {
            delay_500ns();
            digitalWrite(dp->ud_pin, 0);
            delay_500ns();
            digitalWrite(dp->ud_pin, 1);
            dp->setpoint++;
        }
    }
    // Decrement
    else if (value < dp->setpoint)
    {  
        digitalWrite(dp->ud_pin, 0); // Decrement mode
        delay_500ns();
        digitalWrite(dp->cs_pin, 0); // Select device
        while (value != dp->setpoint)
        {
            delay_500ns();
            digitalWrite(dp->ud_pin, 1);
            delay_500ns();
            digitalWrite(dp->ud_pin, 0);
            dp->setpoint--;
        }

    }
    delay_500ns();
    digitalWrite(dp->cs_pin, 1); // De-select device
}

// approximate 500 ns delay
static void delay_500ns()
{
    // Arduino is 16MHz (62.5ns / instr)
    // 500ns = 8 instructions
    //delay(10);
    //__asm__("nop\n\t");
    //__asm__("nop\n\t");
    //__asm__("nop\n\t");
    //__asm__("nop\n\t");
    //__asm__("nop\n\t");
    //__asm__("nop\n\t");
    //__asm__("nop\n\t");
    __asm__("nop\n\t");
}
