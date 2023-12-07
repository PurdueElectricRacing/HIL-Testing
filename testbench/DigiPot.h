#ifndef _DIGIPOT_H_
#define _DIGIPOT_H_

#include <stdint.h>


// Driver for MCP4021T-202E/SN

#define DIGIPOT_STEPS 64
#define DIGIPOT_INIT  31 // from factory

// need U/D line
// need the various CS lines

typedef struct
{
    uint8_t cs_pin;   // chip select pin
    uint8_t ud_pin;   // up down pin
    uint8_t setpoint; // wiper posiiton
} digipot_t;

#ifdef __cplusplus
 extern "C" {
#endif
/**
 * @brief Initializes digipot pins
 *        Initial value is set by factory, or can
 *        be written to eeprom via command.
 * 
 * @param cs_pin     Chip Select Pin Number
 * @param ud_pin     Up Down Pin Number
 * @param start_val  Initial wiper position
 * @param dp         Empty config
 */
void digipot_init(uint8_t cs_pin, uint8_t ud_pin, digipot_t *dp);

/**
 * @brief Set the digipot wiper position
 *        can block over 64us
 * 
 * @param value Value (max of DIGIPOT_STEPS)
 * @param dp          (digipot config)
 */
void digipot_set(uint8_t value, digipot_t *dp);

#ifdef __cplusplus
}
#endif

#endif
