#include <cc2530.h>
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
} uartPacket_t;

// Network settings
#define PAN 0x2016
#define CHANNEL 26
#define TX_POWER 0xF5

// LED settings
#define RED_LED 1

// Global variables
rfConfig_t rfConfig;
configurationPacket_t configurationPacket;
txPacket_t txPacket;
rxPacket_t rxPacket;
uartPacket_t uartPacket;
signed char rssi = 0;
unsigned char sensorId = 0;
unsigned char packetId = 0;

void initialize_uart() {
    CLKCONCMD = CLKCONSTA & 0xB8; // Clock control
    while(CLKCONSTA & 0x40);

    PERCFG &= ~0x01; // Alternative 1 selected for UART0 peripheral
    P0SEL |= 0x3C; // P0.2 and P0.3 peripheral mode enabled with RTS/CTS
    U0CSR |= 0x80; // UART mode selected for USART0
    U0UCR |= 0x42; // Flow control (RTS/CTS) enabled
    U0GCR |= 0x08; // Baud rate exponent
    U0BAUD = 0x3B; // Baud rate mantissa (set to 9600)
    P0DIR |= 0x18; // RTS, TX out
    P0DIR &= ~0x24; // CTS, RX in
    U0CSR |= 0x40; // Enable receiver
}

void initialize() {
    // Initialize LEDs and UART
    ledInit();
    initialize_uart();

    // Initialize the radio module
    rfConfig.addr = PAN;
    rfConfig.pan = PAN;
    rfConfig.channel = CHANNEL;
    rfConfig.txPower = TX_POWER;
    radioInit(&rfConfig);

    // Enable interrupts 
    EA = 1;
}

unsigned char peek() {
    // Check if at least one byte is available in the buffer.
    return U0CSR & 0x04;
}

char read() {
    // Read one byte from the RX buffer.
    while(!URX0IF);
    U0DBUF;
    URX0IF = 0;
    return U0DBUF;
}

void receive(unsigned char* buffer, int length) {
    // Receive data of `length` bytes.
    int i;
    for(i = 0; i < length; i++) {
        buffer[i] = read();
    }
}

void write(unsigned char c) {
    // Write one byte to the TX buffer.
    UTX0IF = 0;
    U0DBUF = c;
    while(!UTX0IF);
    UTX0IF = 0;
}

void send(unsigned char* buffer, int length) {
    // Send data of `length` bytes.
    int i;
    for(i = 0; i < length; i++) {
        write(buffer[i]);
    }
}

void copy(unsigned char* source, unsigned char* destination) {
    // Copy a source data array to a destination data array.
    int i;
    for(i = 0; i < PACKET_LENGTH; i++) {
        destination[i] = source[i];
    }
}

void processUart() {
    // Process incoming configuration or TX packets from UART
    ledOn(RED_LED);

    packetId = read();

    switch(packetId) {
        case CONFIGURATION_PACKET:
            receive((unsigned char*)&configurationPacket, sizeof(configurationPacket));
            sensorId = configurationPacket.sensorId;
            rfConfig.addr = PAN + sensorId;
            radioInit(&rfConfig);
            break;

        case TX_PACKET:
            receive((unsigned char*)&txPacket, sizeof(txPacket));
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
            // Clear the RX buffer
            RFST = 0xED;

            // Transfer the packet over UART
            uartPacket.length = rxPacket.length;
            copy(rxPacket.data, uartPacket.data);
            uartPacket.rssi = rssi;
            send((unsigned char*)&uartPacket, sizeof(uartPacket));
        }
    }
}

void main() {
    initialize();

    while(1) {
        if(peek()) {
            processUart();
        }
        processRadio();
    }
}
