#!/usr/bin/python
#import the libraries we will use in our program
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.GPIO as GPIO
import time
import math
import sys

#set version number
VERSION = "v0.01a"

#set Celsius to kelvin constant
c2kelvin = 273.15

#set the variables we'll use in our calculations
#global variables used when reading AIN0
R_BIAS = 52000 #resistor value used in the thermistor voltage divider
VDD_ADC = 1.8 #voltage divider input voltage
AIN_MIN = .7 #minimum voltage used during self test - will adjust as needed
AIN_MAX = 1.3 #maximum voltage used during self test - will adjust as needed

######### GLOBAL VARIABLE START HERE ##############################
#other global variables
USE_CELSIUS = False #set to 0 to use fahrenheit
HEATER_ON = False #initialize HEATER_ON to False
COOLER_ON = False #initialize COOLER_ON to false

DESIRED_TEMP = 81.5 #set initial desired temp
DWELL = 0.1 #set initial dwell temp range

TIME_LAST_COOLER = 0 #variable to track when cooler was last turned off
COOLER_TIME = 5 * 60 #5 minutes * 60 seconds

OLD_TEMP = 0

#thermistor constants used in polynomial equation
T_a = 7.602330993E-4
T_b = 2.313331379E-4
T_c = 7.172007260E-8

#setup the BBB IO pins
ADC.setup() #setup ADC pins
GPIO.setup("P9_15", GPIO.OUT) #setup pin P9_48 as output pin HEATER
GPIO.setup("P9_23", GPIO.OUT) #setup pin P9_49 as output pin COOLER

GPIO.setup("P9_15", GPIO.OUT) #setup pin P9_48 as output pin HEATER
GPIO.setup("P9_23", GPIO.OUT) #setup pin P9_49 as output pin COOLER

######### FUNCTIONS START HERE #####################################

#self test function to check AIN0 voltage is w/in normal range and GPIO pins/LEDs are working
#we use a function so we can call this code at a later time if we want
def self_test():
  print ('\n' * 80)
  print "BREW CHAMBER CONTROLLER",VERSION
  print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

  print "By: My BBB Projects\n\n\n\n\n\n\n\n"



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

#heater control function
def heater_control(current_temperature):
    global HEATER_ON, DESIRED_TEMP, DWELL
    if current_temperature < DESIRED_TEMP - DWELL:
      if not HEATER_ON:
          HEATER_ON = True
          #print "\033[8;0HHeater: ON "
          GPIO.output("P9_15",GPIO.HIGH)
    elif HEATER_ON:
      HEATER_ON = False
      #print "\033[8;0HHeater: OFF"
      GPIO.output("P9_15",GPIO.LOW)

    if HEATER_ON: 
      print "\033[8;0HHeater: \033[91mON \033[0m"
    else: 
      print "\033[8;0HHeater: OFF"

    return

#cooler control function
def cooler_control(current_temperature):
    global COOLER_ON, DESIRED_TEMP, DWELL, TIME_LAST_COOLER, COOLER_TIME
    if current_temperature > DESIRED_TEMP + DWELL:
      if time.time() - TIME_LAST_COOLER > COOLER_TIME:#has it been more than 5 minutes?
        if not COOLER_ON:
          COOLER_ON = True
          #print "\033[7;0HCooler: ON "
          GPIO.output("P9_23",GPIO.HIGH)
      else: print "\033[7;12H\033[93m| Cooler can't turn on yet", round(300 - (time.time() - TIME_LAST_COOLER),0),"seconds left\033[0m"
    elif COOLER_ON:
      COOLER_ON = False
      #print "\033[7;0HCooler OFF"
      GPIO.output("P9_23",GPIO.LOW)
      TIME_LAST_COOLER = time.time()#reset cooler timer

    if COOLER_ON: 
      print "\033[7;0HCooler: \033[94mON \033[0m                                              "
    else: 
      print "\033[7;0HCooler OFF"

    return

#trend function calculates whether temp went up or down or stayed the same since last checked
#may make this an averaging function so we check the current temp compared to last # averages
def trend_function(OLD_TEMP, current_temperature):
  if current_temperature > OLD_TEMP: TREND = "^"
  elif current_temperature < OLD_TEMP: TREND ="v"
  else: TREND = "-"

  return TREND

########### MAIN PROGRAM STARTS HERE #####################################

self_test()

print "Press CTRL-C to exit program"

#main program loop
input = 1
while input > 0:

    #call the calculate temperature function and assign the results to current temperature
    current_temperature = calculate_temperature()

    #call the heater function and pass the current temperature
    heater_control(current_temperature)

    #call the cooler function and pass the current temperature
    cooler_control(current_temperature)

    print "\033[10;0HDesired temp:",DESIRED_TEMP,"| Current temp:",round(current_temperature,1),\
          "| Trend:",trend_function(OLD_TEMP, current_temperature),"     "

    OLD_TEMP = current_temperature #set OLD_TEMP to current for trend

    print "\033[10;0H"
    
    for x in xrange(15):
      sys.stdout.write('.')
      sys.stdout.flush()
      time.sleep(1) #sleep for 1 second and repeat while True loop
    
    print "\033[10;0H\n                "



