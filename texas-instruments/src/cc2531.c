#include <cc2530.h>
#include "hal_board.h"
#include "hal_led.h"
#include "hal_uart.h"
#include "rf.h"
#include "leds.h"

// Packet definitions
#define CONFIGURATION_PACKET 1
#define TX_PACKET 2

typedef struct {
    unsigned int source;
} configurationPacket_t;

typedef struct {
    unsigned int destination;
} txPacket_t;

typedef struct {
    unsigned int source;
} rxPacket_t;

typedef struct {
    unsigned int source;
    signed int rssi;
} usbPacket_t;

// Network settings
#define PAN 0x2016
#define CHANNEL 26
#define TX_POWER 0xF5

// LED settings
#define RED_LED 2

// Global variables
rfConfig_t rfConfig;
configurationPacket_t configurationPacket;
txPacket_t txPacket;
rxPacket_t rxPacket;
usbPacket_t usbPacket;
signed char rssi = 0;
unsigned int source = 0;
unsigned int id = 0;

// USB handler
void usbirqHandler();
void usb_irq_handler() __interrupt 6 {
    usbirqHandler();
}

void initialize() {
    // Initialize the board, LEDs and USB
    ledInit();
    halBoardInit();
    halUartInit(HAL_UART_BAUDRATE_38400);

    // Initialize the radio module
    rfConfig.addr = PAN;
    rfConfig.pan = PAN;
    rfConfig.channel = CHANNEL;
    rfConfig.txPower = TX_POWER;
    radioInit(&rfConfig);

    // Enable interrupts 
    EA = 1;
}

void processUsb() {
    // Process incoming configuration or TX packets from the USB connection
    ledOn(RED_LED);

    halUartRead((uint8*)&id, sizeof(id));

    switch(id) {
        case CONFIGURATION_PACKET:
            halUartRead((uint8*)&configurationPacket, sizeof(configurationPacket));
            source = configurationPacket.source;
            rfConfig.addr = PAN + source;
            radioInit(&rfConfig);
            break;

        case TX_PACKET:
            halUartRead((uint8*)&txPacket, sizeof(txPacket));
            rxPacket.source = source;
            sendPacket((char*)&rxPacket, sizeof(rxPacket), rfConfig.pan,
                       PAN + txPacket.destination, rfConfig.addr);
            break;
    }

    ledOff(RED_LED);
}

void processRadio() {
    // Process incoming RX packets on the radio module (for RSSI measurements)
    if(isPacketReady()) {
        if(receivePacket((char*)&rxPacket, sizeof(rxPacket), &rssi) == sizeof(rxPacket)) {
            ledOn(RED_LED);

            // Clear the RX buffer
            RFST = 0xED;

            // Transfer the packet over USB
            usbPacket.source = rxPacket.source;
            usbPacket.rssi = rssi;
            halUartWrite((uint8*)&usbPacket, sizeof(usbPacket));

            ledOff(RED_LED);
        }
    }
}

void main() {
    initialize();

    while(1) {
        HAL_PROCESS();

        if(halUartGetNumRxBytes() > 0) {
            processUsb();
        }

        processRadio();
    }
}
