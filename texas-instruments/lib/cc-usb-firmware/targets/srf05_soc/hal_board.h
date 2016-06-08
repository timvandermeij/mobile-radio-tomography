/***********************************************************************************

  Filename:     hal_board.h

  Description:  SmartRF05 board with CCxxxxEM.

***********************************************************************************/

#ifndef HAL_BOARD_H
#define HAL_BOARD_H

#if (chip==2430)
#include "ioCC2430.h"
#elif (chip==2431)
#include "ioCC2431.h"
#elif (chip==2530 || chip==2531)
#include "cc2530.h"
#elif (chip==2510)
#include "ioCC2510.h"
#elif (chip==2511)
#include "ioCC2511.h"
#elif (chip==1110)
#include "ioCC1110.h"
#elif (chip==1111)
#include "ioCC1111.h"
#else
#error "Chip not supported!"
#endif

#include "hal_cc8051.h"
#include "hal_defs.h"
#include "hal_mcu.h"

/***********************************************************************************
 * CONSTANTS
 */

// Board properties
#define BOARD_NAME                     "SRF05EB"
#define NUM_LEDS                        4
#define NUM_POTS                        1

// Clock
#if (chip==2430) || (chip==2431) || (chip==2530) || (chip==2531)
#define BSP_CONFIG_CLOCK_MHZ                32
#elif (chip==2510) || (chip==1110)
#define BSP_CONFIG_CLOCK_MHZ                26
#endif

// SPI
#define HAL_BOARD_IO_SPI_MISO_PORT     1
#define HAL_BOARD_IO_SPI_MISO_PIN      7
#define HAL_BOARD_IO_SPI_MOSI_PORT     1
#define HAL_BOARD_IO_SPI_MOSI_PIN      6
#define HAL_BOARD_IO_SPI_CLK_PORT      1
#define HAL_BOARD_IO_SPI_CLK_PIN       5
#define HAL_BOARD_IO_EM_CS_PORT        1
#define HAL_BOARD_IO_EM_CS_PIN         4

// LEDs
#define HAL_BOARD_IO_LED_1_PORT        1   // Green
#define HAL_BOARD_IO_LED_1_PIN         0
#define HAL_BOARD_IO_LED_2_PORT        1   // Red
#define HAL_BOARD_IO_LED_2_PIN         1
#define HAL_BOARD_IO_LED_3_PORT        1   // Yellow
#define HAL_BOARD_IO_LED_3_PIN         4
#define HAL_BOARD_IO_LED_4_PORT        0   // Orange
#define HAL_BOARD_IO_LED_4_PIN         1

// Potmeter
#define HAL_POTMETER_ADC_PORT               0
#define HAL_POTMETER_ADC_CH                 7

// UART
#define HAL_BOARD_IO_UART_RTS_PORT          0
#define HAL_BOARD_IO_UART_RTS_PIN           5

// Debounce
#define HAL_DEBOUNCE(expr)    { int i; for (i=0; i<500; i++) { if (!(expr)) i = 0; } }

/***********************************************************************************
 * MACROS
 */

// LED

#ifdef SRF05EB_VERSION_1_3
// SmartRF05EB rev 1.3 has only one accessible LED
#define HAL_LED_SET_1()                 MCU_IO_SET_HIGH(HAL_BOARD_IO_LED_1_PORT, HAL_BOARD_IO_LED_1_PIN)
#define HAL_LED_SET_2()
#define HAL_LED_SET_3()
#define HAL_LED_SET_4()

#define HAL_LED_CLR_1()                 MCU_IO_SET_LOW(HAL_BOARD_IO_LED_1_PORT, HAL_BOARD_IO_LED_1_PIN)
#define HAL_LED_CLR_2()
#define HAL_LED_CLR_3()
#define HAL_LED_CLR_4()

#define HAL_LED_TGL_1()                 MCU_IO_TGL(HAL_BOARD_IO_LED_1_PORT, HAL_BOARD_IO_LED_1_PIN)
#define HAL_LED_TGL_2()
#define HAL_LED_TGL_3()
#define HAL_LED_TGL_4()

#else
// SmartRF05EB rev 1.7 and later has four LEDs available
#define HAL_LED_SET_1()                 MCU_IO_SET_HIGH(HAL_BOARD_IO_LED_1_PORT, HAL_BOARD_IO_LED_1_PIN)
#define HAL_LED_SET_2()                 MCU_IO_SET_HIGH(HAL_BOARD_IO_LED_2_PORT, HAL_BOARD_IO_LED_2_PIN)
#define HAL_LED_SET_3()                 MCU_IO_SET_HIGH(HAL_BOARD_IO_LED_3_PORT, HAL_BOARD_IO_LED_3_PIN)
#define HAL_LED_SET_4()                 MCU_IO_SET_HIGH(HAL_BOARD_IO_LED_4_PORT, HAL_BOARD_IO_LED_4_PIN)

#define HAL_LED_CLR_1()                 MCU_IO_SET_LOW(HAL_BOARD_IO_LED_1_PORT, HAL_BOARD_IO_LED_1_PIN)
#define HAL_LED_CLR_2()                 MCU_IO_SET_LOW(HAL_BOARD_IO_LED_2_PORT, HAL_BOARD_IO_LED_2_PIN)
#define HAL_LED_CLR_3()                 MCU_IO_SET_LOW(HAL_BOARD_IO_LED_3_PORT, HAL_BOARD_IO_LED_3_PIN)
#define HAL_LED_CLR_4()                 MCU_IO_SET_LOW(HAL_BOARD_IO_LED_4_PORT, HAL_BOARD_IO_LED_4_PIN)

#define HAL_LED_TGL_1()                 MCU_IO_TGL(HAL_BOARD_IO_LED_1_PORT, HAL_BOARD_IO_LED_1_PIN)
#define HAL_LED_TGL_2()                 MCU_IO_TGL(HAL_BOARD_IO_LED_2_PORT, HAL_BOARD_IO_LED_2_PIN)
#define HAL_LED_TGL_3()                 MCU_IO_TGL(HAL_BOARD_IO_LED_3_PORT, HAL_BOARD_IO_LED_3_PIN)
#define HAL_LED_TGL_4()                 MCU_IO_TGL(HAL_BOARD_IO_LED_4_PORT, HAL_BOARD_IO_LED_4_PIN)
#endif

// UART RTS
#define HAL_RTS_SET()       MCU_IO_SET_HIGH(HAL_BOARD_IO_UART_RTS_PORT, \
    HAL_BOARD_IO_UART_RTS_PIN)
#define HAL_RTS_CLR()       MCU_IO_SET_LOW(HAL_BOARD_IO_UART_RTS_PORT, \
    HAL_BOARD_IO_UART_RTS_PIN)
#define HAL_RTS_DIR_OUT()   MCU_IO_OUTPUT(HAL_BOARD_IO_UART_RTS_PORT, \
    HAL_BOARD_IO_UART_RTS_PIN, 1)

// HAL processing not required for this board
#define HAL_PROCESS()

/***********************************************************************************
 * FUNCTION PROTOTYPES
 */
void halBoardInit(void);

#endif
