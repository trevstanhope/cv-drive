/*
  AutoTill 2
  Electro-Hydraulic PWM Controller
  Developed by Trevor Stanhope
  Receives serial commands to adjust the hydraulics with user-inputted sensitivity settings
*/

/* --- Definitions --- */
#define DURATION_PIN A0
#define REFERENCE_PIN 5
#define CONTROL_PIN 6 // 255 corresponds to reaction at max negative offset

/* --- Constants --- */
const unsigned long BAUD = 9600;
const unsigned int DURATION_MIN = 3;
const unsigned int DURATION_MAX = 30;
const unsigned int PWM_MIN = 0; // AnalogWrite(0) == 0% PWM
const unsigned int PWM_MAX = 255; // AnalogWrite(255) == 100% PWM

/* --- Variables --- */
volatile int DUTY = 127; // effective range of 0 to 255
volatile int DURATION = DURATION_MIN; // default to 1:1
volatile int PWM_CONTROL = 127; // neutral at 127
volatile int PWM_REFERENCE = PWM_MAX; // neutral at 127

void setup(void) {
    pinMode(DURATION_PIN, INPUT);
    pinMode(CONTROL_PIN, OUTPUT);
    pinMode(REFERENCE_PIN, OUTPUT);
    Serial.begin(BAUD);
}

void loop(void) {
    //DURATION = get_duration();
    //Serial.println(DURATION);
    DUTY = Serial.parseInt();
    PWM_CONTROL = DUTY;
    PWM_REFERENCE = PWM_MAX; 
    analogWrite(CONTROL_PIN, PWM_CONTROL);
    analogWrite(REFERENCE_PIN, PWM_REFERENCE);
}

int get_duration(void) {
    int val = analogRead(DURATION_PIN);
    return (DURATION_MAX*(val/ (float) 1024)  + DURATION_MIN);
}
