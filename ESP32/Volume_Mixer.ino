// =========================================================
// ESP32-S3 PyMixer Arduino Code
// Reads 5 analog knobs and 10 digital buttons and
// sends the values as a single, pipe-separated string
// over Serial.
// =========================================================

// Define the number of inputs for clarity
const int NUM_KNOBS = 5;
const int NUM_BUTTONS = 10;
const int BAUD_RATE = 115200;

// Define the GPIO pins for the knobs (potentiometers)
const int knobPins[NUM_KNOBS] = {1, 2, 3, 4, 5};

// Define the GPIO pins for the buttons
const int buttonPins[NUM_BUTTONS] = {6, 7, 8, 9, 10, 11, 12, 13, 14, 15};

// Define the interval in milliseconds to send data.
// Sending too fast can overload the serial buffer.
const long SEND_INTERVAL = 100; // Update 20 times per second (1000ms / 50ms)
long lastSendTime = 0;

void setup() {
  // Start the serial communication at the specified baud rate.
  // This must match the BAUD_RATE in your Python script.
  Serial.begin(BAUD_RATE);
  
  // Set up the button pins as inputs with internal pull-up resistors.
  // This means the pin will be HIGH by default, and go LOW when the button is pressed
  // (connected to GND).
  for (int i = 0; i < NUM_BUTTONS; i++) {
    pinMode(buttonPins[i], INPUT_PULLUP);
  }
}

void loop() {
  // Use millis() for non-blocking timing, which is more reliable than delay().
  if (millis() - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = millis();
    
    // --- READ KNOB VALUES ---
    // Read the analog value (0-4095) from each knob and
    // map it to the 0-1023 range expected by the Python script.
    // Print the first knob value without a leading pipe.
    Serial.print(map(analogRead(knobPins[0]), 0, 4095, 0, 1023));

    // Print the remaining knob values, each preceded by a pipe character.
    for (int i = 1; i < NUM_KNOBS; i++) {
      Serial.print('|');
      Serial.print(map(analogRead(knobPins[i]), 0, 4095, 0, 1023));
    }
    
    // --- READ BUTTON VALUES ---
    // Read the state of each button.
    // The internal pull-up resistor means HIGH=not pressed, LOW=pressed.
    // We invert this to send a '1' for pressed and '0' for not pressed.
    for (int i = 0; i < NUM_BUTTONS; i++) {
      Serial.print('|');
      // The `!digitalRead()` inverts the value:
      // if LOW (pressed), it becomes 1 (true)
      // if HIGH (not pressed), it becomes 0 (false)
      Serial.print(!digitalRead(buttonPins[i]));
    }
    
    // --- FINISH THE MESSAGE ---
    // Print a newline character to mark the end of the data packet.
    // This allows the Python script's `ser.readline()` to work correctly.
    Serial.println();
  }
}
