#!/usr/bin/python
#import the libraries we will use in our program
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.GPIO as GPIO
import time
import math
import sys
import select

#set version number
VERSION = "v0.02a"

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
USE_CELSIUS = False #set to 0 to use Fahrenheit
HEATER_ON = False #initialize HEATER_ON to False
COOLER_ON = False #initialize COOLER_ON to false

DESIRED_TEMP = 65 #set initial desired temp
DWELL = 1 #set initial dwell temp range

TIME_LAST_COOLER = 0 #variable to track when cooler was last turned off
COOLER_TIME = 5 * 60 #5 minutes * 60 seconds

OLD_TEMP = 0
MIN_TEMP = 0
MAX_TEMP = 0

current_temperature = 0

#used to wait for one minute to allow moving average temperature to stabilize
PROGRAM_START_TIME = time.time() 

#thermistor constants used in polynomial equation
T_a = 7.602330993E-4
T_b = 2.313331379E-4
T_c = 7.172007260E-8

#setup the BBB IO pins
ADC.setup() #setup ADC pins
GPIO.setup("P9_15", GPIO.OUT) #setup pin P9_48 as output pin HEATER
GPIO.setup("P9_23", GPIO.OUT) #setup pin P9_49 as output pin COOLER



######### FUNCTIONS START HERE #####################################

#print output#######################################################
def print_output():

  print "\033[10;0H                                                                                                      "

  print "\033[10;0HDwell:",DWELL,"| Desired temp:",DESIRED_TEMP,"| Current temp:",\
         round(current_temperature,1),"| Trend:",trending.trend,"| Min:",\
         round(MIN_TEMP,1),"| Max:",round(MAX_TEMP,1),"| Rdgs:",round(trending.temp1,1),\
         round(trending.temp2,1),round(trending.temp3,1),round(trending.temp4,1),\
         "| MAvg:",round(trending.moving_avg_temp,1)

  return

#check for user input###############################################
def check_input():

  if select.select([sys.stdin],[],[],0.0)[0]:
    key_input = sys.stdin.readline()

    if key_input[0] == 's' or key_input[0] == 'S':
      set_desired_temp()

    if key_input[0] == 'd' or key_input[0] == 'D':
      set_dwell()

    if key_input[0] == 'x' or key_input[0] == 'X':
      exit_program()

    print_output()
    heater_control(trending.moving_avg_temp)
    cooler_control(trending.moving_avg_temp)
    print_menu()
    print "\033[12;0H                  "
    print "\033[10;0H"

  return

#exit program######################################################
def exit_program():
  print "\033[24;0HExiting program..."
  time.sleep(2)
  exit(0)

#set dwell#########################################################
def set_dwell():
  global DWELL

  print "\033[24;0H"
  DWELL = input("Enter dwell: ")
  print "\033[25;0H                                   "
 
  return

#set desired temperature##########################################
def set_desired_temp():
  global DESIRED_TEMP

  print "\033[24;0H"
  DESIRED_TEMP = input("Enter desired temperature: ")
  print "\033[25;0H                                  "

  return

#delay_loop function#############################################
def delay_loop():
  print "\033[10;0H"
    
  for x in xrange(15):
    if x % 5 == 0: print "\033[11;0HRunning: ."
    if x % 5 == 1: print "\033[11;0HRunning: o"
    if x % 5 == 2: print "\033[11;0HRunning: O"
    if x % 5 == 3: print "\033[11;0HRunning: 0"
    if x % 5 == 4: print "\033[11;0HRunning: *"

    check_input()

    time.sleep(1) #sleep for 1 second and repeat while True loop

  return

#print title##################################################
def print_title():

  print "\033[2J" #clear screen
  print "\033[2;0HBREW CHAMBER CONTROLLER",VERSION
  print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

  print "By: My BBB Projects\n\n\n\n\n\n\n\n"

  return

#print menu##################################################
def print_menu():
  print "\033[12;0H" #menu goes here
  
  print "                     =====================MENU===================="
  print "                     |S - Set Temp | D - Set Dwell |             |"
  print "                     |             |               |             |"
  print "                     |             |               |             |"
  print "                     |             |               |             |"
  print "                     |             |               |             |"
  print "                     |             |               |             |"
  print "                     |             |               |             |"
  print "                     |             |               | X - Exit    |"
  print "                     ============================================="

  return


#self test####################################################
#function to check AIN0 voltage is w/in normal range and GPIO pins/LEDs are working
#we use a function so we can call this code at a later time if we want
def self_test():

  print "Performing self test..."
  time.sleep(1) #sleep for 1 second to slow down test sequence - change/remove if desired
  #turn on heater LED
  print "Turning on RED LED"
  GPIO.output("P9_15",GPIO.HIGH)
  time.sleep(0.1)
  print "Turning off RED LED"
  GPIO.output("P9_15",GPIO.LOW)
  time.sleep(0.1)
  print "Turning on GREEN LED"
  GPIO.output("P9_23",GPIO.HIGH)
  time.sleep(0.1)
  print "Turning off GREEN LED"
  GPIO.output("P9_23",GPIO.LOW)
  time.sleep(0.1)

  adcValue = ADC.read("AIN0") * VDD_ADC

  if adcValue > AIN_MIN and adcValue < AIN_MAX: print "adcValue OK: ", adcValue

  #time.sleep(1)
  print "Test complete\n\n"
  
  print "Type X [enter] to exit program"

  time.sleep(1)

  return

#calculate temperature function################################
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

#heater control function#######################################
def heater_control(MAvg_temp):
    global HEATER_ON, DESIRED_TEMP, DWELL

    if time.time() - PROGRAM_START_TIME < 60:
      print "\033[8;0H\033[93mHeater: OFF - pausing for avg temp stabilization...\033[0m"
      return

    if MAvg_temp < DESIRED_TEMP - DWELL:
      if not HEATER_ON:
          HEATER_ON = True
          #print "\033[8;0HHeater: ON "
          GPIO.output("P9_15",GPIO.HIGH)
    elif HEATER_ON:
      HEATER_ON = False
      #print "\033[8;0HHeater: OFF"
      GPIO.output("P9_15",GPIO.LOW)

    if HEATER_ON: 
      print "\033[8;0HHeater: \033[91mON \033[0m                                              "
    else: 
      print "\033[8;0HHeater: OFF                                                             "

    return

#cooler control function######################################
def cooler_control(MAvg_temp):
    global COOLER_ON, DESIRED_TEMP, DWELL, TIME_LAST_COOLER, COOLER_TIME

    if time.time() - PROGRAM_START_TIME < 60:
      print "\033[7;0H\033[93mCooler: OFF - pausing for avg temp stabilization...\033[0m"
      return

    if MAvg_temp > DESIRED_TEMP + DWELL:
      if time.time() - TIME_LAST_COOLER > COOLER_TIME: #has it been more than 5 minutes?
        if not COOLER_ON:
          COOLER_ON = True
          GPIO.output("P9_23",GPIO.HIGH)
      else:
        print "\033[7;0HCooler: OFF\033[7;12H\033[93m | Cooler can't turn on yet:", round(300-(time.time()-\
                   TIME_LAST_COOLER),0),"seconds left     \033[0m"
        return
    elif COOLER_ON:
      COOLER_ON = False
      GPIO.output("P9_23",GPIO.LOW)
      TIME_LAST_COOLER = time.time()#reset cooler timer

    if COOLER_ON: 
      print "\033[7;0HCooler: \033[94mON \033[0m                                              "
    else: 
      print "\033[7;0HCooler: OFF                                                              "

    return

#Trend Class##############################################
#calculates whether temp went up or down or stayed the same since last checked
#may make this an averaging function so we check the current temp compared to last # averages

class Trend:

  def __init__(self):#######################

    #initialize static variables
    self.trend ="-"
    self.moving_avg_temp = 0
    self.temp1 = 0
    self.temp2 = 0
    self.temp3 = 0
    self.temp4 = 0

    return


  def move_average(self):#Called every 15 seconds from main program loop#

    #move the temperatures through the 4 variables
    #since this is updated every 15 seconds there is one minute of data stored here
    self.temp4 = self.temp3
    self.temp3 = self.temp2
    self.temp2 = self.temp1
    self.temp1 = current_temperature

    self.set_average() #average the 4 values
    self.set_trend() #set the trend indicator

    return


  def set_trend(self):######################

    if current_temperature > self.moving_avg_temp+.01: self.trend = "^" #upward trend
    elif current_temperature < self.moving_avg_temp-.01: self.trend = "v" #downward trend
    else: self.trend = "-"
    
    return


  def set_average(self):###################

    self.moving_avg_temp = (self.temp1 + self.temp2 + self.temp3 + self.temp4) / 4

    return



########### MAIN PROGRAM STARTS HERE #####################################

print_title()
self_test()

trending = Trend()
move_average = trending.move_average

#main program loop##########################################
_input = 1
while _input > 0:

    #call the calculate temperature function and assign the results to current temperature
    current_temperature = calculate_temperature()

    #call the heater function and pass the current temperature
    heater_control(trending.moving_avg_temp)

    #call the cooler function and pass the current temperature
    cooler_control(trending.moving_avg_temp)

    #move the trend average
    move_average()

    #set the MIN and MAX temps
    if current_temperature > MAX_TEMP:
       MAX_TEMP = current_temperature

    if MIN_TEMP == 0: MIN_TEMP = MAX_TEMP

    if current_temperature < MIN_TEMP:
      MIN_TEMP = current_temperature

    print_output()

#    OLD_TEMP = current_temperature #set OLD_TEMP to current for trend

    delay_loop()

    print_menu()

    print "\033[10;0H\n                "

exit(0)



