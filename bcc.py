#!/usr/bin/python
#import the libraries we will use in our program
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.GPIO as GPIO
import time
import math
import sys
import select

######### GLOBAL VARIABLE START HERE ##############################
#set version number
#major release . minor release . bugfix
VERSION = "v0.03.1a"

#set Celsius to kelvin constant
c2kelvin = 273.15

#set the variables we'll use in our calculations
#global variables used when reading AIN0
R_BIAS = 52000 #resistor value used in the thermistor voltage divider
VDD_ADC = 1.8 #voltage divider input voltage
AIN_MIN = .7 #minimum voltage used during self test - will adjust as needed
AIN_MAX = 1.3 #maximum voltage used during self test - will adjust as needed

#other global variables
HEATER_ON = False #initialize HEATER_ON to False
COOLER_ON = False #initialize COOLER_ON to false

TIME_LAST_COOLER = 0 #variable to track when cooler was last turned off
COOLER_TIME = 5 * 60 #5 minutes * 60 seconds

OLD_TEMP = 0
MIN_TEMP = 0
MAX_TEMP = 0

current_temperature = 0

#alarm variables:
IS_ALARM = False
ALARM_HIGH_TEMP = False
ALARM_LOW_TEMP = False
ALARM_COOLER_MALFUNC = False
ALARM_HEATER_MALFUNC = False

TIME_BEFORE_ALARM_TRIGGER = 5 * 60 #(5 minutes in seconds)

#used to wait for one minute to allow moving average temperature to stabilize
PROGRAM_START_TIME = time.time() 

#brew cycle variable
#Off, Normal Brew, Warm Brew, Lager, Cold Crash, Clearing
BREW_CYCLE = "Off  "

USE_CELSIUS = False #set to 0 to use Fahrenheit


if USE_CELSIUS:
  TEMP_SCALE = "Celsius"
  LAGER_TEMP = 7
  WARM_TEMP = 21
  NORM_TEMP = 18
  CRASH_TEMP = 2
  CLEAR_TEMP = 10
  DESIRED_TEMP = 18 #set initial desired temp
  DWELL = 1.2 #set initial dwell temp range
  #alarm threshold variables:
  MAX_HIGH_TEMP = 24
  MIN_LOW_TEMP = 1
else:
  TEMP_SCALE = "Fahrenheit"
  LAGER_TEMP = 45
  WARM_TEMP = 70
  NORM_TEMP = 65
  CRASH_TEMP = 35
  CLEAR_TEMP = 50
  DESIRED_TEMP = 65 #set initial desired temp
  DWELL = 2.5 #set initial dwell temp range
  #alarm threshold variables:
  MAX_HIGH_TEMP = 75
  MIN_LOW_TEMP = 34

#thermistor constants used in polynomial equation
T_a = 7.602330993E-4
T_b = 2.313331379E-4
T_c = 7.172007260E-8

#setup the BBB IO pins
ADC.setup() #setup ADC pins
GPIO.setup("P9_15", GPIO.OUT) #setup pin P9_48 as output pin HEATER
GPIO.setup("P9_23", GPIO.OUT) #setup pin P9_49 as output pin COOLER



######### FUNCTIONS START HERE #####################################

#check for user input###############################################
def check_input():

  if select.select([sys.stdin],[],[],0.0)[0]:
    key_input = sys.stdin.readline()

    if key_input[0] == 'a' or key_input[0] == 'A':
      set_alarm_thresholds()

    if key_input[0] == 'c' or key_input[0] == 'C':
      clear_brew()

    if key_input[0] == 'd' or key_input[0] == 'D':
      set_dwell()

    if key_input[0] == 'f' or key_input[0] == 'F':
      draw_screen()

    if key_input[0] == 'l' or key_input[0] == 'L':
      lager()

    if key_input[0] == 'n' or key_input[0] == 'N':
      normal_brew()

    if key_input[0] == 'o' or key_input[0] == 'O':
      brew_off()

    if key_input[0] == 'r' or key_input[0] == 'R':
      crash_brew()

    if key_input[0] == 's' or key_input[0] == 'S':
      switch_scale()

    if key_input[0] == 't' or key_input[0] == 'T':
      set_desired_temp()

    if key_input[0] == 'w' or key_input[0] == 'W':
      warm_brew()

    if key_input[0] == 'x' or key_input[0] == 'X':
      exit_program()

    print_output()
    check_alarms()
    heater_control(O_trending.moving_avg_temp)
    cooler_control(O_trending.moving_avg_temp)

  return

def switch_scale():
  global USE_CELSIUS,LAGER_TEMP,WARM_TEMP,NORM_TEM,CRASH_TEMP,CLEAR_TEMP,DESIRED_TEMP,DWELL,MAX_HIGH_TEMP
  global MIN_LOW_TEMP,MAX_TEMP,MIN_TEMP,TEMP_SCALE,current_temperature

  if USE_CELSIUS: #switch to Fahrenheit
    USE_CELSIUS = False
    TEMP_SCALE = "Fahrenheit"
    MAX_TEMP = (MAX_TEMP * 9/5) + 32
    MIN_TEMP = (MIN_TEMP * 9/5) + 32
    O_trending.temp1 = (O_trending.temp1 * 9/5) + 32
    O_trending.temp2 = (O_trending.temp2 * 9/5) + 32
    O_trending.temp3 = (O_trending.temp3 * 9/5) + 32
    O_trending.temp4 = (O_trending.temp4 * 9/5) + 32
    O_trending.moving_avg_temp = (O_trending.moving_avg_temp * 9/5) + 32
    current_temperature = (current_temperature * 9/5) + 32
  else: 
    USE_CELSIUS = True #else switch to Celsius
    TEMP_SCALE = "Celsius"
    MAX_TEMP = (MAX_TEMP -32) * 5 / 9
    MIN_TEMP = (MIN_TEMP -32) * 5 / 9
    O_trending.temp1 = (O_trending.temp1 -32) * 5 / 9
    O_trending.temp2 = (O_trending.temp2 -32) * 5 / 9
    O_trending.temp3 = (O_trending.temp3 -32) * 5 / 9
    O_trending.temp4 = (O_trending.temp4 -32) * 5 / 9
    O_trending.moving_avg_temp = (O_trending.moving_avg_temp -32) * 5 / 9
    current_temperature = (current_temperature -32) * 5 / 9


  if USE_CELSIUS:
    LAGER_TEMP = 7
    WARM_TEMP = 21
    NORM_TEMP = 18
    CRASH_TEMP = 2
    CLEAR_TEMP = 10
    DESIRED_TEMP = (DESIRED_TEMP -32) * 5 / 9
    DWELL = 1.2
    MAX_HIGH_TEMP = 24
    MIN_LOW_TEMP = 1
  else:
    LAGER_TEMP = 45
    WARM_TEMP = 70
    NORM_TEMP = 65
    CRASH_TEMP = 35
    CLEAR_TEMP = 50
    DESIRED_TEMP = (DESIRED_TEMP * 9/5) + 32
    DWELL = 2.5
    MAX_HIGH_TEMP = 75
    MIN_LOW_TEMP = 34

  return

#off cycle#######################################################
def brew_off():
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP

  BREW_CYCLE = "Off  "

  if USE_CELSIUS:
    DESIRED_TEMP = 18
    MAX_HIGH_TEMP = 24
    MIN_LOW_TEMP = 1
  else:
    DESIRED_TEMP = 65
    MAX_HIGH_TEMP = 75
    MIN_LOW_TEMP = 34

  return

#clear cycle#######################################################
def clear_brew():
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP

  BREW_CYCLE = "Clear"

  if USE_CELSIUS:
    DESIRED_TEMP = CLEAR_TEMP #10
    MAX_HIGH_TEMP = CLEAR_TEMP + 2
    MIN_LOW_TEMP = CLEAR_TEMP - 2
  else:
    DESIRED_TEMP = CLEAR_TEMP #50
    MAX_HIGH_TEMP = CLEAR_TEMP + 5
    MIN_LOW_TEMP = CLEAR_TEMP - 5

  return

#normal cycle#######################################################
def normal_brew():
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP

  BREW_CYCLE = "Norm "

  if USE_CELSIUS:
    DESIRED_TEMP = NORM_TEMP #18
    MAX_HIGH_TEMP = NORM_TEMP + 2
    MIN_LOW_TEMP = NORM_TEMP - 2
  else:
    DESIRED_TEMP = NORM_TEMP #65
    MAX_HIGH_TEMP = NORM_TEMP + 5
    MIN_LOW_TEMP = NORM_TEMP - 5

  return

#crash cycle#######################################################
def crash_brew():
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP

  BREW_CYCLE = "Crash"

  if USE_CELSIUS:
    DESIRED_TEMP = CRASH_TEMP #1.6
    MAX_HIGH_TEMP = CRASH_TEMP + 2
    MIN_LOW_TEMP = CRASH_TEMP - 1
  else:
    DESIRED_TEMP = CRASH_TEMP #35
    MAX_HIGH_TEMP = CRASH_TEMP + 5
    MIN_LOW_TEMP = CRASH_TEMP - 2

  return

#warm cycle#######################################################
def warm_brew():
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP

  BREW_CYCLE = "Warm "

  if USE_CELSIUS:
    DESIRED_TEMP = WARM_TEMP #21
    MAX_HIGH_TEMP = WARM_TEMP + 2
    MIN_LOW_TEMP = WARM_TEMP - 2
  else:
    DESIRED_TEMP = WARM_TEMP #70
    MAX_HIGH_TEMP = WARM_TEMP + 5
    MIN_LOW_TEMP = WARM_TEMP - 5

  return

#lager cycle#######################################################
def lager():
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP

  BREW_CYCLE = "Lager"

  if USE_CELSIUS:
    DESIRED_TEMP = LAGER_TEMP #10
    MAX_HIGH_TEMP = LAGER_TEMP + 2
    MIN_LOW_TEMP = LAGER_TEMP - 2
  else:
    DESIRED_TEMP = LAGER_TEMP #45
    MAX_HIGH_TEMP = LAGER_TEMP + 5
    MIN_LOW_TEMP = LAGER_TEMP - 2

  return

#set alarm thresholds##############################################
def set_alarm_thresholds():
  global MAX_HIGH_TEMP,MIN_LOW_TEMP


  while True:
    print "\033[16;0H"
    try:
      MAX_HIGH_TEMP = input("Enter max temp for alarm: ")
      break
    except:
      print "Enter a numeric value"


  while True:
    print "\033[16;0H\033[0K"
    try:
      MIN_LOW_TEMP = input("Enter min temp for alarm: ")
      break
    except:
      print "Enter a numeric value"

  print "\033[17;0H\033[0K"
  print "\033[18;0H\033[0K"
  return

#set dwell#########################################################
def set_dwell():
  global DWELL

  while True:
    print "\033[16;0H"
    try:
      DWELL = input("Enter dwell: ")
      break
    except:
      print "Enter a numerical value"
      print "\033[16;0H\033[0K"

  print "\033[17;0H\033[0K"
  print "\033[18;0H\033[0K"

  return

#set desired temperature##########################################
def set_desired_temp():
  global DESIRED_TEMP


  while True:
    print "\033[16;0H"
    try:
      DESIRED_TEMP = input("Enter desired temperature: ")
      break
    except:
      print "Enter a numerical value"

  print "\033[17;0H\033[0K"
  print "\033[18;0H\033[0K"

  return

#exit program######################################################
def exit_program():
  print "\033[16;0HExiting program..."

  #do some shutdown stuff here if desired

  time.sleep(2)
  exit(0)

#delay_loop function#############################################
def delay_loop():
  #delay for 15 seconds/check user input every second/display running indicator
    
  for x in xrange(15):
    if x % 5 == 0: print "\033[15;20H[    =    ]"
    if x % 5 == 1: print "\033[15;20H[   =-=   ]"
    if x % 5 == 2: print "\033[15;20H[  =-=-=  ]"
    if x % 5 == 3: print "\033[15;20H[ =-=-=-= ]"
    if x % 5 == 4: print "\033[15;20H[=-=-=-=-=]"

    print "\033[16;0H\033[0K\033[15;0H"

    check_input()

    time.sleep(1) #sleep for 1 second and repeat while True loop

  return

#self test####################################################
#function to check AIN0 voltage is w/in normal range and GPIO pins/LEDs are working
#we use a function so we can call this code at a later time if we want
def self_test():

  print "\033[2J" #clear screen
  print "\033[2;0HBREW CHAMBER CONTROLLER",VERSION
  print "\033[3;0H~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
  print "\033[4;0HBy: My BBB Projects"

  print "\033[6;0H\033[0KPerforming self test..."
  time.sleep(1) #sleep for 1 second to slow down test sequence - change/remove if desired
  #turn on heater LED
  print "\033[7;0H\033[0KTurning on RED LED"
  GPIO.output("P9_15",GPIO.HIGH)
  time.sleep(0.1)
  print "\033[8;0H\033[0KTurning off RED LED"
  GPIO.output("P9_15",GPIO.LOW)
  time.sleep(0.1)
  print "\033[9;0H\033[0KTurning on GREEN LED"
  GPIO.output("P9_23",GPIO.HIGH)
  time.sleep(0.1)
  print "\033[10;0H\033[0KTurning off GREEN LED"
  GPIO.output("P9_23",GPIO.LOW)
  time.sleep(0.1)

  adcValue = ADC.read("AIN0") * VDD_ADC

  if adcValue > AIN_MIN and adcValue < AIN_MAX: 
    print "\033[11;0H\033[0KadcValue OK:", adcValue
  else: 
    print "\033[11;0H\033[0K\033[31madcValue Out Of Bounds:",adcValue,"\033[39m"
    exit(0)

  #time.sleep(1)
  print "\033[12;0H\033[0KTest complete"
  
  print "\033[13;0H\033[0KType X [enter] to exit program"

  time.sleep(2)

  print "\033[2J" #clear screen
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

#cooler control function######################################
def cooler_control(MAvg_temp):
    global COOLER_ON, DESIRED_TEMP, DWELL, TIME_LAST_COOLER, COOLER_TIME

    if time.time() - PROGRAM_START_TIME < 60:
      COOLER_ON = False
      GPIO.output("P9_23",GPIO.LOW)
      print "\033[25;0H\033[93m Cooler: OFF\033[0m"
      return
    
    if BREW_CYCLE == "Off  ":
      COOLER_ON = False
      print "\033[25;0H Cooler: OFF      "
      GPIO.output("P9_23",GPIO.LOW)
      return
      
    if MAvg_temp > DESIRED_TEMP + DWELL:
      if time.time() - TIME_LAST_COOLER > COOLER_TIME: #has it been more than 5 minutes?
        if not COOLER_ON:
          COOLER_ON = True
          GPIO.output("P9_23",GPIO.HIGH)
      else:
        print "\033[25;0H\033[93m Cooler: OFF", round(300-(time.time()-TIME_LAST_COOLER),0),"\033[39m"
        return
    elif COOLER_ON:
      COOLER_ON = False
      GPIO.output("P9_23",GPIO.LOW)
      TIME_LAST_COOLER = time.time()#reset cooler timer

    if COOLER_ON: 
      print "\033[25;0H Cooler: \033[94mON      \033[0m"
    else: 
      print "\033[25;0H Cooler: OFF      "

    return

#heater control function#######################################
def heater_control(MAvg_temp):
    global HEATER_ON, DESIRED_TEMP, DWELL

    if time.time() - PROGRAM_START_TIME < 60:
      print "\033[26;0H\033[93m Heater: OFF\033[0m"
      return

    if BREW_CYCLE == "Off  ":
      HEATER_ON = False
      print "\033[26;0H Heater: OFF      "
      GPIO.output("P9_15",GPIO.LOW)
      return

    if MAvg_temp < DESIRED_TEMP - DWELL:
      if not HEATER_ON:
          HEATER_ON = True
          GPIO.output("P9_15",GPIO.HIGH)
    elif HEATER_ON:
      HEATER_ON = False
      GPIO.output("P9_15",GPIO.LOW)

    if HEATER_ON: 
      print "\033[26;0H Heater: \033[91mON \033[0m"
    else: 
      print "\033[26;0H Heater: OFF"

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

    if current_temperature > self.moving_avg_temp+.02: self.trend = "^" #upward trend
    elif current_temperature < self.moving_avg_temp-.02: self.trend = "v" #downward trend
    else: self.trend = "-"
    
    return


  def set_average(self):###################

    self.moving_avg_temp = (self.temp1 + self.temp2 + self.temp3 + self.temp4) / 4

    return

#set the minimum and maximum temperatures###############################
def min_max():
  global MAX_TEMP, MIN_TEMP, current_temperature

  #set the MIN and MAX temps
  if current_temperature > MAX_TEMP:
     MAX_TEMP = current_temperature

  if MIN_TEMP == 0: MIN_TEMP = MAX_TEMP

  if current_temperature < MIN_TEMP:
    MIN_TEMP = current_temperature

  return

#check alarms###########################################################
def check_alarms():
  global IS_ALARM,ALARM_HIGH_TEMP,ALARM_LOW_TEMP,ALARM_COOLER_MALFUNC,ALARM_HEATER_MALFUNC, MAX_HIGH_TEMP,MIN_LOW_TEMP,TIME_BEFORE_ALARM_TRIGGER,BREW_CYCLE

#exit function if program has just started
  if time.time() - PROGRAM_START_TIME < 60:
    print "\033[24;35H\033[93mOFF\033[39m"
    return

  if BREW_CYCLE == "Off  ":
    IS_ALARM = False
    ALARM_LOW_TEMP = False
    ALARM_HIGH_TEMP = False
    print "\033[24;35HOFF"

    display_alarm()

    return

  print "\033[24;35H\033[32mON \033[39m"
#check for over or under temperature condition
  if O_trending.moving_avg_temp > MAX_HIGH_TEMP:
    ALARM_HIGH_TEMP = True
  else:
    ALARM_HIGH_TEMP = False

  if O_trending.moving_avg_temp < MIN_LOW_TEMP:
    ALARM_LOW_TEMP = True
  else:
    ALARM_LOW_TEMP = False

  if ALARM_LOW_TEMP or ALARM_HIGH_TEMP:
    IS_ALARM = True
  else:
    ALARM_LOW_TEMP = False
    ALARM_HIGH_TEMP = False
    IS_ALARM =False

#alarm function should check if cooler or heater is running and if temp is adjusting over time accordingly

  display_alarm()

  print "\033[25;20H|  HT:",MAX_HIGH_TEMP,"| LT:",MIN_LOW_TEMP 

  return

#display alarms on screen#################################################
def display_alarm():
  global ALARM_HIGH_TEMP,ALARM_LOW_TEMP

  if ALARM_HIGH_TEMP:
    print "\033[26;35H\033[31mON \033[39m"
  else:
    print "\033[26;35HOFF"

  if ALARM_LOW_TEMP:
    print "\033[27;35H\033[31mON \033[39m"
  else:
    print "\033[27;35HOFF"
  
  return

#draw screen##############################################################
def draw_screen():

  print "\033[2J" #clear screen
  print "\033[2;0HBREW CHAMBER CONTROLLER",VERSION
  print "\033[3;0H~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
  print "\033[4;0HBy: My BBB Projects"



  print "\033[5;0H"
  print "\033[6;0H----------------------=MENU=---------------------"
  print "\033[7;0H| S - Scale(C/F)| A - Alarms    | C - Clear     |"     
  print "\033[8;0H| T - Set Temp  | F - Refresh   | L - Lager     |"
  print "\033[9;0H| D - Set Dwell |               | N - Normal    |"
  print "\033[10;0H|               |               | O - Off       |"
  print "\033[11;0H|               |               | R - Crash     |"
  print "\033[12;0H|               |               | W - Warm      |"
  print "\033[13;0H|               |               |               |"
  print "\033[14;0H|               |               | X - Exit      |"
  print "\033[15;0H===================[         ]==================="

  print "\033[23;0H\033[0K--=Brew Status=--"
  print "\033[24;0H\033[0K Brew Cycle:     "
  print "\033[25;0H\033[0K Cooler:         "
  print "\033[26;0H\033[0K Heater:         "
  print "\033[27;0H\033[0K",TEMP_SCALE
  print "\033[28;0H\033[0K                 "

  print "\033[23;20H\033[0K| --=Alarm Status=--"
  print "\033[24;20H\033[0K|  System:"
  print "\033[25;20H\033[0K|  HT:",MAX_HIGH_TEMP,"| LT:",MIN_LOW_TEMP 
  print "\033[26;20H\033[0K|  High Temp:  OFF"
  print "\033[27;20H\033[0K|  Low Temp:   OFF"
  print "\033[28;20H\033[0K|  Malfunc:    OFF"

  print "\033[23;39H\033[0K | -----------------=System Status=-------------------"
  print "\033[24;39H\033[0K |  Dsrd Temp:        "
  print "\033[25;39H\033[0K |  Crnt Temp:        "
  print "\033[26;39H\033[0K |  Trend:            "
  print "\033[27;39H\033[0K |  Min:              "
  print "\033[28;39H\033[0K |  Max:              "

  print "\033[24;61H\033[0K |  T1:       "
  print "\033[25;61H\033[0K |  T2:       "
  print "\033[26;61H\033[0K |  T3:       "
  print "\033[27;61H\033[0K |  T4:       "
  print "\033[28;61H\033[0K |  MAvg:     "

  print "\033[24;77H\033[0K |  Dwell:    "
  print "\033[25;77H\033[0K |            "
  print "\033[26;77H\033[0K |            "
  print "\033[27;77H\033[0K |            "
  print "\033[28;77H\033[0K |            "

  #print "\n\n"
  #exit(0)
  return

#print output#######################################################
def print_output():

  #print the variables
  print "\033[24;13H",BREW_CYCLE

  print "\033[27;1H",TEMP_SCALE,"   "

  print "\033[24;55H",round(DESIRED_TEMP,1)
  print "\033[25;55H",round(current_temperature,1)
  print "\033[26;55H",O_trending.trend
  print "\033[27;55H",round(MIN_TEMP,1)
  print "\033[28;55H",round(MAX_TEMP,1)

  print "\033[24;71H",round(O_trending.temp1,1)
  print "\033[25;71H",round(O_trending.temp2,1)
  print "\033[26;71H",round(O_trending.temp3,1)
  print "\033[27;71H",round(O_trending.temp4,1)
  print "\033[28;71H",round(O_trending.moving_avg_temp,1)

  print "\033[24;88H\033[0K",DWELL
  return

########### MAIN PROGRAM STARTS HERE #####################################
self_test()
draw_screen()

O_trending = Trend()
move_average = O_trending.move_average

#main program loop##########################################
_input = 1
while _input > 0:

    #call the calculate temperature function and assign the results to current temperature
    current_temperature = calculate_temperature()

    #call the heater function and pass the current temperature
    heater_control(O_trending.moving_avg_temp)

    #call the cooler function and pass the current temperature
    cooler_control(O_trending.moving_avg_temp)

    #move the trend average
    move_average()

    #set the min and max temperatures
    min_max()

    #check alarms
    check_alarms()

    #update the screen
    print_output()

    #15 second delay/indicate the program is running/check for user input
    delay_loop()

    #clear line 10 of the screen
    #print "\033[10;0H\033[0K\n"

exit(0)



