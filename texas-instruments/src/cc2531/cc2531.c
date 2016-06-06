#include <cc2530.h>
#include "hal_board.h"
#include "hal_uart.h"
#include "rf.h"
#include "leds.h"

// Packet definitions
#define PACKET_LENGTH 80
#define CONFIGURATION_PACKET 1
#define TX_PACKET 2

typedef struct {
    unsigned char sensorId;
} configurationPacket_t;

typedef struct {
    unsigned char destination;
    unsigned char length;
    unsigned char data[PACKET_LENGTH];
} txPacket_t;

typedef struct {
    unsigned char length;
    unsigned char data[PACKET_LENGTH];
} rxPacket_t;

typedef struct {
    unsigned char length;
    unsigned char data[PACKET_LENGTH];
    signed char rssi;
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
unsigned char sensorId = 0;
unsigned char packetId = 0;

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

void copy(unsigned char* source, unsigned char* destination) {
    // Copy a source data array to a destination data array.
    int i;
    for(i = 0; i < PACKET_LENGTH; i++) {
        destination[i] = source[i];
    }
}

void processUsb() {
    // Process incoming configuration or TX packets from USB
    ledOn(RED_LED);

    halUartRead((uint8*)&packetId, sizeof(packetId));

    switch(packetId) {
        case CONFIGURATION_PACKET:
            halUartRead((uint8*)&configurationPacket, sizeof(configurationPacket));
            sensorId = configurationPacket.sensorId;
            rfConfig.addr = PAN + sensorId;
            radioInit(&rfConfig);
            break;

        case TX_PACKET:
            halUartRead((unsigned char*)&txPacket, sizeof(txPacket));
            rxPacket.length = txPacket.length;
            copy(txPacket.data, rxPacket.data);
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
            usbPacket.length = rxPacket.length;
            copy(rxPacket.data, usbPacket.data);
            usbPacket.rssi = rssi;
            halUartWrite((unsigned char*)&usbPacket, sizeof(usbPacket));

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
