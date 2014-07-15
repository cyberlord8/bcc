#!/usr/bin/python
#import the libraries we will use in our program
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.GPIO as GPIO
import time
import math

#set Celsius to kelvin constant
c2kelvin = 273.15

#set the variables we'll use in our calculations
#global variables used when reading AIN0
R_BIAS = 52000 #resistor value used in the thermistor voltage divider
VDD_ADC = 1.8 #voltage divider input voltage
AIN_MIN = .7 #minimum voltage used during self test - will adjust as needed
AIN_MAX = 1.3 #maximum voltage used during self test - will adjust as needed

#other global variables
USE_CELSIUS = 0 #set to 0 to use fahrenheit
HEATER_ON = 0 #initialize HEATER_ON to False
COOLER_ON = 0 #initialize COOLER_ON to false
DESIRED_TEMP = 78 #set initial desired temp
DWELL = 2 #set initial dwell temp range

#thermistor constants used in polynomial equation
T_a = 7.602330993E-4
T_b = 2.313331379E-4
T_c = 7.172007260E-8

#setup the BBB IO pins
ADC.setup() #setup ADC pins
GPIO.setup("P9_15", GPIO.OUT) #setup pin P9_48 as output pin HEATER
GPIO.setup("P9_23", GPIO.OUT) #setup pin P9_49 as output pin COOLER

#self test function to check AIN0 voltage is w/in normal range and GPIO pins/LEDs are working
#we use a function so we can call this code at a later time if we want
def self_test():
  print "Performing self tests"
  time.sleep(1) #sleep for 1 second to slow down test sequence - remove if desired
  #turn on heater LED
  print "Turning on RED LED"
  GPIO.output("P9_15",GPIO.HIGH)
  time.sleep(1)
  print "Turning off RED LED"
  GPIO.output("P9_15",GPIO.LOW)
  time.sleep(1)
  print "Turning on GREEN LED"
  GPIO.output("P9_23",GPIO.HIGH)
  time.sleep(1)
  print "Turning off GREEN LED"
  GPIO.output("P9_23",GPIO.LOW)
  time.sleep(1)

  adcValue = ADC.read("AIN0") * VDD_ADC

  if adcValue > AIN_MIN and adcValue < AIN_MAX: print "adcValue OK: ", adcValue

  time.sleep(1)
  print "Test complete\n\n"
  time.sleep(1)
  return

#calculate temperature function

def calculate_temperature():
    #define global variables
    global VDD_ADC, R_BIAS, c2kelvin, T_a, T_b, T_c, USE_CELSIUS

    #read AIN0 pin and calculate voltage 
    Vout = ADC.read("AIN0") * VDD_ADC

    #calculate thermistor resistance R1
    res_therm = R_BIAS * (VDD_ADC - Vout) / Vout

    #calculate temperature in kelvin
    temp_kelvin = 1/(T_a + T_b * math.log(res_therm) + T_c * pow(math.log(res_therm),3))
    temp_celsius = temp_kelvin - c2kelvin
    temp_fahren = (temp_celsius * 9/5) + 32

    if USE_CELSIUS: return temp_celsius
    else: return temp_fahren

def heater_control(current_temperature):
    global HEATER_ON, DESIRED_TEMP, DWELL
    if current_temperature < DESIRED_TEMP - DWELL:
      if not HEATER_ON:
        HEATER_ON = True
        print "Turning heater on\n\n"
        GPIO.output("P9_15",GPIO.HIGH)
    elif HEATER_ON:
      HEATER_ON = False
      print "Turning heater off\n\n"
      GPIO.output("P9_15",GPIO.LOW)
    return

def cooler_control(current_temperature):
    global COOLER_ON, DESIRED_TEMP, DWELL
    if current_temperature > DESIRED_TEMP + DWELL:
      if not COOLER_ON:
        COOLER_ON = True
        print "Turning cooler on\n\n"
        GPIO.output("P9_23",GPIO.HIGH)
    elif COOLER_ON:
      COOLER_ON = False
      print "Turning cooler off\n\n"
      GPIO.output("P9_23",GPIO.LOW)
    return

self_test()

while True:

    #call the calculate temperature function and assign the results to current temperature
    current_temperature = calculate_temperature()

    print "Current temperature:",round(current_temperature,1)

    #call the heater function and pass the current temperature
    heater_control(current_temperature)

    #call the cooler function and pass the current temperature
    cooler_control(current_temperature)

    time.sleep(5) #sleep for 5 seconds and repeat while True loop
