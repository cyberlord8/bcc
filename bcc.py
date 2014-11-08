#!/usr/bin/python
# This program is designed to run on a Beaglebone Black. 
# You will need to install the Adafruit BBB-IO Python library.
# If you want to use charting you will also need to install gnuplot and gnuplot-x11
#
# Licensing is as follows:
# http://opensource.org/licenses/GPL-3.0

"""
    bcc.py - Beer brewing temperature controller
    Copyright (C) 2014,  Timothy J. Millea

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, version 3 of the License.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see http://www.gnu.org/licenses.
"""

#import the libraries we will use in our program
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.GPIO as GPIO
import time
import math
import sys
import select
import csv
import os

######### GLOBAL VARIABLE START HERE ##############################
#set version number
#major release . minor release . bugfix
VERSION = "v0.07.0a"

#set Celsius to kelvin constant
c2kelvin = 273.15

#set the variables we'll use in our calculations
#global variables used when reading AIN0
R_BIAS = 52000 #resistor value used in the thermistor voltage divider
VDD_ADC = 1.8 #voltage divider input voltage
AIN_MIN = .3 #minimum voltage used during self test - will adjust as needed
AIN_MAX = 1.7 #maximum voltage used during self test - will adjust as needed

#yeast profile global variables
Y_PROF_ID = 0 #yeast profile ID
Y_LAB = "none" #yeast LAB
Y_NUM = "none" #yeast LAB Number
Y_NAME = "none" #yeast name
Y_STYLE = "none" #Beer style
Y_LOW_TEMP = 0 #recommended yeast low temp
Y_HIGH_TEMP = 0 #recommended yeast high temp
Y_DESC = "none"

#brew info variables
BREW_NAME = "none"
BREW_BATCH_NUM = "none"
BREW_BATCH_SIZE = 0.0
BREW_STYLE = "none"
BREW_METHOD = "none"
BREW_SESSION_FILENAME = "none"

#other global variables
HEATER_ON = False #initialize HEATER_ON to False
COOLER_ON = False #initialize COOLER_ON to false

TIME_LAST_COOLER = 0 #variable to track when cooler was last turned off
COOLER_TIME = 5 * 60 #5 minutes * 60 seconds

LAST_TIME_DATABASE = 0 #variable to track last database update was made
DATABASE_INTERVAL = 15 * 60 #15 minutes * 60 seconds

LAST_BREW_SESSION_TIME = 0
CHARTING_ON = False
CHARTING_INTERVAL = 1 * 60 #15 minutes - adjustable in program
DATA_TO_PLOT = False
NUM_DATA_POINTS = 0
PLOT_STARTED = False

current_temperature = 0

#alarm variables:
ALARM_SYS_ON = False
IS_ALARM = False
ALARM_HIGH_TEMP = False
ALARM_LOW_TEMP = False
ALARM_COOLER_MALFUNC = False
ALARM_HEATER_MALFUNC = False
TIME_LAST_SMS = 0 #used to track sms message interval
SMS_INTERVAL = 60 * 60 #60minutes * 60 seconds
SMS_ALARM_ON = False

TIME_BEFORE_ALARM_TRIGGER = 5 * 60 #(5 minutes in seconds)

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


#read in the settings file
from bccconfig import *

if TEMP_SCALE == "Celsius": #from import bccconfig above
  USE_CELSIUS = True

elif TEMP_SCALE == "Fahrenheit":
  USE_CELSIUS = False


######### FUNCTIONS START HERE #####################################

######### AUTOMATION FUNCTIONS #####################################



######### USER INPUT FUNCTIONS #####################################

#check for user input###############################################
def check_input():

  if select.select([sys.stdin],[],[],0.0)[0]:
    key_input = sys.stdin.readline()

    if key_input[0] == 'a' or key_input[0] == 'A':
      set_alarm_thresholds()

    if key_input[0] == 'b' or key_input[0] == 'B':
      get_brew_info()

    if key_input[0] == 'c' or key_input[0] == 'C':
      clear_brew()

    if key_input[0] == 'd' or key_input[0] == 'D':
      set_dwell()

    if key_input[0] == 'f' or key_input[0] == 'F':
      draw_screen()

    if key_input[0] == 'g' or key_input[0] == 'G':
      chart_graphics()

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

    if key_input[0] == 'y' or key_input[0] == 'Y':
      yeast_profile()

    draw_screen()
    print_output()

    check_alarms()

    heater_control(O_trending.moving_avg_temp)
    cooler_control(O_trending.moving_avg_temp)

    write_settings()
    update_database()

  return

#charting options######################################################################
def chart_graphics():

  global CHARTING_ON,CHARTING_INTERVAL

  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      charting_on = raw_input("Turn charting graphics on (yes/no): ")
      break
    except:
      print "Enter yes or no"

  if charting_on.lower() == "yes":
    CHARTING_ON = True
    while True:
      print "\033[17;0H\033[0K\033[16;0H"
      try:
        minutes = input("Enter charting interval in minutes: ")
        break
      except:
        print "Enter a number"
    CHARTING_INTERVAL = minutes * 60 #convert to seconds
  else: CHARTING_ON = False

  return

#get_brew_info#########################################################################
#get information about brew session from user
def get_brew_info():
  global BREW_NAME,BREW_BATCH_NUM,BREW_BATCH_SIZE,BREW_STYLE,BREW_METHOD,Y_PROF_ID,BREW_CYCLE,BREW_SESSION_FILENAME, \
         PLOT_STARTED,NUM_DATA_POINTS,DATA_TO_PLOT

  from datetime import datetime

  print "\033[16;0H\033[0KThis will start a new brew session."

  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      BREW_NAME = raw_input("Enter brew name: ")
      break
    except:
      print "Enter brew name"

  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      BREW_BATCH_NUM = raw_input("Enter brew batch number: ")
      break
    except:
      print "Enter brew batch number"

  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      BREW_BATCH_SIZE = input("Enter brew batch size: ")
      break
    except:
      print "Enter a number"

  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      BREW_STYLE = raw_input("Enter brew style: ")
      break
    except:
      print "Enter brew style"

  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      BREW_METHOD = raw_input("Enter brew method: ")
      break
    except:
      print "Enter brew name"

  yeast_profile()

  database_file = open("database.csv", "a")

  database_file.write(str(BREW_NAME)+", "+str(BREW_BATCH_NUM)+", "+str(BREW_BATCH_SIZE)+", "+str(BREW_STYLE)+", "+
                      str(BREW_METHOD)+", "+str(Y_PROF_ID)+", "+str(Y_NAME)+"\n")

  database_file.close()

  BREW_CYCLE = "Off  "

  reset_min_max()
  DATA_TO_PLOT = False
  NUM_DATA_POINTS = 0
  PLOT_STARTED = False


  BREW_SESSION_FILENAME = './data/'+BREW_NAME + '-' + BREW_BATCH_NUM + '-' + str(BREW_BATCH_SIZE) + '-' + BREW_STYLE + '-' + BREW_METHOD

  init_gnuplot_script()

  return

#yeast_profile#########################################################################
#open the yeast strains csv file and store it in a tuple
def yeast_profile():
  global Y_PROF_ID,Y_LAB,Y_NUM,Y_NAME,Y_STYLE,Y_DESC,Y_LOW_TEMP,Y_HIGH_TEMP #yeast
  global LAGER_TEMP,WARM_TEMP,NORM_TEMP,CRASH_TEMP,CLEAR_TEMP,DESIRED_TEMP,DWELL,MAX_HIGH_TEMP,MIN_LOW_TEMP #temps

  Y_ID = 0

  print "\033[16;0HReading yeast strains file..."

  #read in the yeast csv file and store it in a tuple (array of arrays)
  try:
    with open('Yeast Strains.csv') as f:
      ytuple=[tuple(line) for line in csv.reader(f)]
  except:
    print "\033[17;0HError reading file"
    return

  while True:
    print "\033[16;0H"
    try:
      Y_ID = input("Enter desired yeast profile ID: ")
      break
    except:
      print "Enter a numeric value"

  #check to see if ID number is within range
  if Y_ID < 1: return
  if Y_ID > len(ytuple) - 1: return

  #switch to Fahrenheit to store the variables
  if USE_CELSIUS:
    switch_scale()

    #store the tuple info in the global yeast variables
    Y_PROF_ID = int(Y_ID)
    Y_LAB = ytuple[Y_PROF_ID][1]
    Y_NUM = ytuple[Y_PROF_ID][2]
    Y_NAME = ytuple[Y_PROF_ID][3]
    Y_STYLE = ytuple[Y_PROF_ID][4]
    Y_DESC = ytuple[Y_PROF_ID][5]
    Y_LOW_TEMP = int(ytuple[Y_PROF_ID][6])
    Y_HIGH_TEMP = int(ytuple[Y_PROF_ID][7])

    #set the program variables based on the yeast profile selected
    #norm temp is 1/4 of the difference warmer than the low yeast temp
    #warm temp is 1/4 of the difference cooler that the high yeast temp
    NORM_TEMP = Y_LOW_TEMP + ((Y_HIGH_TEMP - Y_LOW_TEMP)/2.0) - ((Y_HIGH_TEMP - Y_LOW_TEMP)/4.0)
    WARM_TEMP = Y_LOW_TEMP + ((Y_HIGH_TEMP - Y_LOW_TEMP)/2.0) + ((Y_HIGH_TEMP - Y_LOW_TEMP)/4.0)
  
    #now switch back
    switch_scale()

  else:
    #store the tuple info in the global yeast variables
    Y_PROF_ID = int(Y_ID)
    Y_LAB = ytuple[Y_PROF_ID][1]
    Y_NUM = ytuple[Y_PROF_ID][2]
    Y_NAME = ytuple[Y_PROF_ID][3]
    Y_STYLE = ytuple[Y_PROF_ID][4]
    Y_DESC = ytuple[Y_PROF_ID][5]
    Y_LOW_TEMP = int(ytuple[Y_PROF_ID][6])
    Y_HIGH_TEMP = int(ytuple[Y_PROF_ID][7])

    #set the program variables based on the yeast profile selected
    #norm temp is 1/4 of the difference warmer than the low yeast temp
    #warm temp is 1/4 of the difference cooler that the high yeast temp
    NORM_TEMP = Y_LOW_TEMP + ((Y_HIGH_TEMP - Y_LOW_TEMP)/2.0) - ((Y_HIGH_TEMP - Y_LOW_TEMP)/4.0)
    WARM_TEMP = Y_LOW_TEMP + ((Y_HIGH_TEMP - Y_LOW_TEMP)/2.0) + ((Y_HIGH_TEMP - Y_LOW_TEMP)/4.0)


  if BREW_CYCLE == 'Norm ': DESIRED_TEMP = NORM_TEMP
  elif BREW_CYCLE == 'Warm ' : DESIRED_TEMP = WARM_TEMP

  MAX_HIGH_TEMP = WARM_TEMP + DWELL
  MIN_LOW_TEMP = NORM_TEMP - DWELL

  print "\033[16;0H\033[0K"
  print "\033[17;0H\033[0K"
  print "\033[18;0H\033[0K"

  return


def switch_scale():
  global USE_CELSIUS,LAGER_TEMP,WARM_TEMP,NORM_TEMP,CRASH_TEMP,CLEAR_TEMP,DESIRED_TEMP,DWELL,MAX_HIGH_TEMP
  global MIN_LOW_TEMP,MAX_TEMP,MIN_TEMP,TEMP_SCALE,current_temperature,Y_LOW_TEMP,Y_HIGH_TEMP

  if USE_CELSIUS: #switch to Fahrenheit
    USE_CELSIUS = False
    TEMP_SCALE = "Fahrenheit"
    MAX_TEMP = (MAX_TEMP * 9.0/5.0) + 32
    MIN_TEMP = (MIN_TEMP * 9.0/5.0) + 32
    O_trending.temp1 = (O_trending.temp1 * 9.0/5.0) + 32
    O_trending.temp2 = (O_trending.temp2 * 9.0/5.0) + 32
    O_trending.temp3 = (O_trending.temp3 * 9.0/5.0) + 32
    O_trending.temp4 = (O_trending.temp4 * 9.0/5.0) + 32
    O_trending.moving_avg_temp = (O_trending.moving_avg_temp * 9.0/5.0) + 32
    current_temperature = (current_temperature * 9.0/5.0) + 32
  else: 
    USE_CELSIUS = True #else switch to Celsius
    TEMP_SCALE = "Celsius"
    MAX_TEMP = (MAX_TEMP -32) * 5.0 / 9.0
    MIN_TEMP = (MIN_TEMP -32) * 5.0 / 9.0
    O_trending.temp1 = (O_trending.temp1 -32) * 5.0 / 9.0
    O_trending.temp2 = (O_trending.temp2 -32) * 5.0 / 9.0
    O_trending.temp3 = (O_trending.temp3 -32) * 5.0 / 9.0
    O_trending.temp4 = (O_trending.temp4 -32) * 5.0 / 9.0
    O_trending.moving_avg_temp = (O_trending.moving_avg_temp -32) * 5.0 / 9.0
    current_temperature = (current_temperature -32) * 5.0 / 9.0


  if USE_CELSIUS:
    LAGER_TEMP = (LAGER_TEMP -32) * 5.0 / 9.0
    WARM_TEMP = (WARM_TEMP -32) * 5.0 / 9.0
    NORM_TEMP = (NORM_TEMP -32) * 5.0 / 9.0
    CRASH_TEMP = (CRASH_TEMP -32) * 5.0 / 9.0
    CLEAR_TEMP = (CLEAR_TEMP -32) * 5.0 / 9.0
    DESIRED_TEMP = (DESIRED_TEMP -32) * 5.0 / 9.0
    MAX_HIGH_TEMP = (MAX_HIGH_TEMP -32) * 5.0 / 9.0
    MIN_LOW_TEMP = (MIN_LOW_TEMP -32) * 5.0 / 9.0
    Y_LOW_TEMP = (Y_LOW_TEMP - 32) * 5.0 / 9.0
    Y_HIGH_TEMP = (Y_HIGH_TEMP - 32) * 5.0 / 9.0
    DWELL = (DWELL)*5.0/9.0

  else:
    LAGER_TEMP = (LAGER_TEMP * 9.0/5.0) + 32
    WARM_TEMP = (WARM_TEMP * 9.0/5.0) + 32
    NORM_TEMP = (NORM_TEMP * 9.0/5.0) + 32
    CRASH_TEMP = (CRASH_TEMP * 9.0/5.0) + 32
    CLEAR_TEMP = (CLEAR_TEMP * 9.0/5.0) + 32
    DESIRED_TEMP = (DESIRED_TEMP * 9.0/5.0) + 32
    MAX_HIGH_TEMP = (MAX_HIGH_TEMP * 9.0/5.0) + 32
    MIN_LOW_TEMP = (MIN_LOW_TEMP * 9.0/5.0) + 32
    Y_LOW_TEMP = (Y_LOW_TEMP * 9.0 / 5.0) + 32
    Y_HIGH_TEMP = (Y_HIGH_TEMP * 9.0 / 5.0) + 32
    DWELL = (DWELL)*9.0/5.0

  print "\033[25;20H|  H",round(MAX_HIGH_TEMP,0),"| L",round(MIN_LOW_TEMP,0) 

  return

#off cycle#######################################################
def brew_off():
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP,USE_CELSIUS,TIME_LAST_COOLER,COOLER_ON

  if BREW_CYCLE == "Off ": pass
  else:
    BREW_CYCLE = "Off  "
    if COOLER_ON:
      COOLER_ON = False
      GPIO.output("P9_23",GPIO.LOW)
      print "\033[25;0H\033[93m Cooler: OFF\033[0m"
      TIME_LAST_COOLER = time.time()#reset cooler timer

  if USE_CELSIUS:
    DESIRED_TEMP = 18
    MAX_HIGH_TEMP = 24
    MIN_LOW_TEMP = 1
  else:
    DESIRED_TEMP = 65
    MAX_HIGH_TEMP = 75
    MIN_LOW_TEMP = 34

  display_alarm()

  return

#clear cycle#######################################################
def clear_brew():
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP,USE_CELSIUS

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
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP,USE_CELSIUS

  BREW_CYCLE = "Norm "

  if USE_CELSIUS:
    DESIRED_TEMP = NORM_TEMP
    MAX_HIGH_TEMP = WARM_TEMP + DWELL
    MIN_LOW_TEMP = NORM_TEMP - DWELL
  else:
    DESIRED_TEMP = NORM_TEMP
    MAX_HIGH_TEMP = WARM_TEMP + DWELL
    MIN_LOW_TEMP = NORM_TEMP - DWELL

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
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP,USE_CELSIUS

  BREW_CYCLE = "Warm "

  if USE_CELSIUS:
    DESIRED_TEMP = WARM_TEMP
    MAX_HIGH_TEMP = WARM_TEMP + DWELL
    MIN_LOW_TEMP = NORM_TEMP - DWELL
  else:
    DESIRED_TEMP = WARM_TEMP
    MAX_HIGH_TEMP = WARM_TEMP + DWELL
    MIN_LOW_TEMP = NORM_TEMP - DWELL

  return

#lager cycle#######################################################
def lager():
  global BREW_CYCLE,DESIRED_TEMP,MAX_HIGH_TEMP,MIN_LOW_TEMP,USE_CELSIUS

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
  global MAX_HIGH_TEMP,MIN_LOW_TEMP,ALARM_SYS_ON,SMS_ALARM_ON

  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      user_input = raw_input("Alarm on (yes/no): ")
      if (user_input.lower() == "yes"):
        ALARM_SYS_ON = True
      else: 
        ALARM_SYS_ON = False
        return
      break
    except:
      print "Enter yes or no"

  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      user_input = raw_input("SMS text messages on (yes/no): ")
      if (user_input == "yes"):
        SMS_ALARM_ON = True
      else: 
        SMS_ALARM_ON = False
      break
    except:
      print "Enter yes or no"

  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      MAX_HIGH_TEMP = input("Enter max temp for alarm: ")
      break
    except:
      print "Enter a numeric value"


  while True:
    print "\033[17;0H\033[0K\033[16;0H"
    try:
      MIN_LOW_TEMP = input("Enter min temp for alarm: ")
      break
    except:
      print "Enter a numeric value"

  print "\033[17;0H\033[0K"
  print "\033[18;0H\033[0K"
  return

#set dwell#################################@##############################
def set_dwell():
  global DWELL,MAX_HIGH_TEMP,MIN_LOW_TEMP,WARM_TEMP,NORM_TEMP

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

  MAX_HIGH_TEMP = WARM_TEMP + DWELL
  MIN_LOW_TEMP = NORM_TEMP - DWELL

  return

#set desired temperature#################################################
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

#exit program############################################################
def exit_program():

  from datetime import datetime
  from os import system

  print "\033[15;0H"

  #do some shutdown stuff here if desired
  print "Writing files..."
  write_settings()

  database_file = open("database.csv", "a")

  database_file.write("bcc.py exiting normally: " + str(datetime.now()) + "\n")

  database_file.close()

  print "Killing gnuplot script..."
  system("pkill -9 gnuplot")

  print "Exiting program..."
  time.sleep(2)
  exit(0)


######### ALARM FUNCTIONS ##############################################

#check alarms###########################################################
def check_alarms():
  global IS_ALARM,ALARM_HIGH_TEMP,ALARM_LOW_TEMP,ALARM_COOLER_MALFUNC,ALARM_HEATER_MALFUNC, MAX_HIGH_TEMP,MIN_LOW_TEMP,TIME_BEFORE_ALARM_TRIGGER,BREW_CYCLE,ALARM_SYS_ON

#exit function if program has just started
  if time.time() - PROGRAM_START_TIME < 60:
    print "\033[24;26H\033[93mOFF\033[39m"
    print "\033[24;36H\033[93mOFF\033[39m"

    return

  if not ALARM_SYS_ON:#if alarm system is off
    print "\033[24;26HOFF\033[39m"
    print "\033[24;36HOFF\033[39m"
    return

  if BREW_CYCLE == "Off  ": #if brew cycle is off
    IS_ALARM = False
    ALARM_LOW_TEMP = False
    ALARM_HIGH_TEMP = False
    display_alarm()
    return

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

  print "\033[25;20H|  H",round(MAX_HIGH_TEMP,0),"| L",round(MIN_LOW_TEMP,0) 

  if IS_ALARM:
    sms_alarm()

  return

#sms_alarm################################################################
def sms_alarm():
  global TIME_LAST_SMS,SMS_INTERVAL

  if SMS_ALARM_ON:
    if (time.time() - TIME_LAST_SMS > SMS_INTERVAL):#check to make sure it's been over an hour
      if ALARM_HIGH_TEMP:
        os.system('curl http://textbelt.com/text -d number='+CELL_NUMBER+' -d "message=bcc alarm - High Temp"')
        TIME_LAST_SMS = time.time()#update time last sent SMS
      elif ALARM_LOW_TEMP:
        os.system('curl http://textbelt.com/text -d number='+CELL_NUMBER+' -d "message=bcc alarm - Low Temp"')
        TIME_LAST_SMS = time.time()#update time last sent SMS

      draw_screen()
      print_output()
      display_alarm()

  return

#display alarms on screen#################################################
def display_alarm():
  global ALARM_HIGH_TEMP,ALARM_LOW_TEMP

  if ALARM_SYS_ON:
    print "\033[24;26H\033[32mON \033[39m"
  else:
    print "\033[24;26HOFF\033[39m" 

  if SMS_ALARM_ON:
    print "\033[24;36H\033[32mON \033[39m"
  else:
    print "\033[24;36HOFF\033[39m"

  if ALARM_HIGH_TEMP:
    print "\033[26;35H\033[31mON \033[39m"
  else:
    print "\033[26;35HOFF"

  if ALARM_LOW_TEMP:
    print "\033[27;35H\033[31mON \033[39m"
  else:
    print "\033[27;35HOFF"

  if BREW_CYCLE == "Off  ":   
    print "\033[24;26HOFF" 
    print "\033[24;36HOFF"
    print "\033[26;35HOFF"
    print "\033[27;35HOFF"
  
  return


######### PROGRAM OPERATION FUNCTIONS ###########################

#delay_loop function#############################################
def delay_loop():
  #delay for 15 seconds/check user input every second/display running indicator
    
  for x in xrange(15):
    if x % 5 == 0: print "\033[15;21H[    =    ]"
    if x % 5 == 1: print "\033[15;21H[   =-=   ]"
    if x % 5 == 2: print "\033[15;21H[  =-=-=  ]"
    if x % 5 == 3: print "\033[15;21H[ =-=-=-= ]"
    if x % 5 == 4: print "\033[15;21H[=-=-=-=-=]"

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
    temp_kelvin = 1.0/(T_a + T_b * math.log(res_therm) + T_c * pow(math.log(res_therm),3.0))
    temp_celsius = temp_kelvin - c2kelvin
    temp_fahren = (temp_celsius * 9.0/5.0) + 32

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
      
    if MAvg_temp > DESIRED_TEMP + DWELL/2.0:
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

    if MAvg_temp < DESIRED_TEMP - DWELL/2.0:
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

    self.moving_avg_temp = (self.temp1 + self.temp2 + self.temp3 + self.temp4) / 4.0

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

#reset min and max temperatures#########################################
def reset_min_max():
  global MAX_TEMP, MIN_TEMP

  MIN_TEMP = 0
  MAX_TEMP = 0

  return


######### DISPLAY FUNCTIONS ##############################################

#draw screen##############################################################
def draw_screen():

  from datetime import datetime

  print "\033[2J" #clear screen
  print "\033[2;0HBREW CHAMBER CONTROLLER",VERSION
  print "\033[3;0H~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
  print "\033[4;0HBy: My BBB Projects"

  print "\033[5;0H"
  print "\033[6;0H-----------------------=MENU=---------------------"
  print "\033[7;0H| S - Scale(C/F) | A - Alarms    | C - Clear     |"     
  print "\033[8;0H| T - Set Temp   | B - New Brew  | L - Lager     |"
  print "\033[9;0H| D - Set Dwell  | F - Refresh   | N - Normal    |"
  print "\033[10;0H| Y - Yeast Prof | G - Graphics  | O - Off       |"
  print "\033[11;0H|                |               | R - Crash     |"
  print "\033[12;0H|                |               | W - Warm      |"
  print "\033[13;0H|                |               |               |"
  print "\033[14;0H|                | X - Exit      |               |"
  print "\033[15;0H====================[         ]==================="

  print "\033[23;0H\033[0K--=Brew Status=--"
  print "\033[24;0H\033[0K Brew Cycle:     "
  print "\033[25;0H\033[0K Cooler:         "
  print "\033[26;0H\033[0K Heater:         "
  print "\033[27;0H\033[0K",TEMP_SCALE
  print "\033[28;0H\033[0K                 "

  print "\033[23;20H\033[0K| --=Alarm Status=--"
  print "\033[24;20H\033[0K| Sys     | SMS "
  print "\033[25;20H\033[0K|  H",round(MAX_HIGH_TEMP,0),"| L",round(MIN_LOW_TEMP,0) 
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
  print "\033[25;77H\033[0K |  Cell: "+CELL_NUMBER
  print "\033[26;77H\033[0K |  "+str(datetime.now().strftime("%Y-%m-%d %H:%M"))
  print "\033[27;77H\033[0K |  Charts: "
  print "\033[28;77H\033[0K |            "

  print "\033[29;0H\033[0K YEAST PROFILE"
  print "\033[30;0H\033[0K",Y_PROF_ID,"|",Y_LAB,"|",Y_NUM,"|",Y_NAME,"|",Y_STYLE,"|",round(Y_LOW_TEMP,1),"|",round(Y_HIGH_TEMP,1)
  print "\033[31;0H\033[0K",Y_DESC

  print "\033[33;0H\033[0K BREW INFO"
  print "\033[34;0H\033[0K",BREW_NAME,"|",BREW_BATCH_NUM,"|",BREW_BATCH_SIZE,"|",BREW_STYLE,"|",BREW_METHOD

  return

#print output#######################################################
def print_output():

  from datetime import datetime

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

  print "\033[26;77H\033[0K |  "+str(datetime.now().strftime("%Y-%m-%d %H:%M"))

  if CHARTING_ON:
    print "\033[27;77H\033[0K |  Charts: ON - "+str(CHARTING_INTERVAL/60)
  else: print "\033[27;77H\033[0K |  Charts: OFF"

  print "\033[24;88H\033[0K",round(DWELL,1)


  print "\033[30;0H\033[0K",Y_PROF_ID,"|",Y_LAB,"|",Y_NUM,"|",Y_NAME,"|",Y_STYLE,"|",round(Y_LOW_TEMP,1),"|",round(Y_HIGH_TEMP,1)
  print "\033[31;0H\033[0K",Y_DESC

  return


######### DATABASE FUNCTIONS ###################################################

#init gnuplot script ####################################################
def init_gnuplot_script():
  global Y_LOW_TEMP,Y_HIGH_TEMP,LOW_TEMP,HIGH_TEMP,BREW_SESSION_FILENAME,LAST_BREW_SESSION_TIME,CHARTING_ON

  if not CHARTING_ON:
    return

  LAST_BREW_SESSION_TIME = 0

  #decide what range to use for the y axis - use the larger value
  if Y_LOW_TEMP < MIN_TEMP: low_scale_temp = round(Y_LOW_TEMP,2)
  else: low_scale_temp = round(MIN_TEMP,2)

  if Y_HIGH_TEMP > MAX_TEMP: high_scale_temp = round(Y_HIGH_TEMP,2)
  else: high_scale_temp = round(MAX_TEMP,2)

  gnuplot_script_file = open(BREW_SESSION_FILENAME+".gp", "w")#create the brew session gnuplot script

  gnuplot_script_file.write("#!/usr/bin/gnuplot\n")
  gnuplot_script_file.write("# bcc.py created gnuplot file\n")
  gnuplot_script_file.write("#\n\n")
  gnuplot_script_file.write("reset\n")
  gnuplot_script_file.write("set xdata time\n")
  gnuplot_script_file.write("set xrange[*:*]\n")
  gnuplot_script_file.write("set timefmt \"%Y-%m-%d %H:%M:%S\"\n")
  gnuplot_script_file.write("set yrange["+str(low_scale_temp-5)+":"+str(high_scale_temp+5)+"]\n")
  gnuplot_script_file.write("set mytics 5\n")
  gnuplot_script_file.write("set xtics 1\n")
  gnuplot_script_file.write("set datafile separator \",\"\n")
  gnuplot_script_file.write("set title \""+BREW_SESSION_FILENAME+"\"\n")
  gnuplot_script_file.write("set xlabel \"Time\"\n")
  gnuplot_script_file.write("set ylabel \"Temperature\"\n")
  gnuplot_script_file.write("set grid\n")
  gnuplot_script_file.write("plot \'"+BREW_SESSION_FILENAME+".dat\' using 1:2 title \"Avg Temp\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:2 title \"Smoothed\" smooth bezier with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:3 title \"Min Temp\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:4 title \"Max Temp\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:5 title \"Des Temp\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:6 title \"Hi Alarm\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:7 title \"Lo Alarm\" with lines\n")
  gnuplot_script_file.write("pause "+str(CHARTING_INTERVAL)+"\n")
  gnuplot_script_file.write("reread\n")

#  gnuplot_script_file.write("pause 1\n")


  gnuplot_script_file.close()

  gnuplot_script_data_file = open(BREW_SESSION_FILENAME+".dat", "w")#create the brew session database
  gnuplot_script_data_file.close()

  return

#update gnuplot script ####################################################
def update_gnuplot_script():
  global Y_LOW_TEMP,Y_HIGH_TEMP,MIN_TEMP,MAX_TEMP,BREW_SESSION_FILENAME,CHARTING_ON

  if not CHARTING_ON:
    return

  #decide what range to use for the y axis - use the larger value
  if Y_LOW_TEMP < MIN_TEMP: low_scale_temp = round(Y_LOW_TEMP,2)
  else: low_scale_temp = round(MIN_TEMP,2)

  if Y_HIGH_TEMP > MAX_TEMP: high_scale_temp = round(Y_HIGH_TEMP,2)
  else: high_scale_temp = round(MAX_TEMP,2)

  gnuplot_script_file = open(BREW_SESSION_FILENAME+".gp", "w")#create the brew session gnuplot script

  gnuplot_script_file.write("#!/usr/bin/gnuplot\n")
  gnuplot_script_file.write("# bcc.py created gnuplot file\n")
  gnuplot_script_file.write("#\n\n")
  gnuplot_script_file.write("reset\n")
  gnuplot_script_file.write("set xdata time\n")
  gnuplot_script_file.write("set format x \"%H:%M\"\n")
  gnuplot_script_file.write("set xrange[*:*]\n")
  gnuplot_script_file.write("set timefmt \"%Y-%m-%d %H:%M:%S\"\n")
  gnuplot_script_file.write("set yrange["+str(low_scale_temp-5)+":"+str(high_scale_temp+5)+"]\n")
  gnuplot_script_file.write("set mytics 5\n")
  gnuplot_script_file.write("set datafile separator \",\"\n")
  gnuplot_script_file.write("set title \""+BREW_SESSION_FILENAME+"\\n"+Y_NAME+"\"\n")
  gnuplot_script_file.write("set xlabel \"Time\"\n")
  gnuplot_script_file.write("set ylabel \"Temperature\"\n")
  gnuplot_script_file.write("set grid\n")
  gnuplot_script_file.write("plot \'"+BREW_SESSION_FILENAME+".dat\' using 1:2 title \"Avg Temp\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:2 title \"Smoothed\" smooth bezier with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:3 title \"Min Temp\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:4 title \"Max Temp\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:5 title \"Des Temp\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:6 title \"Hi Alarm\" with lines\n")
  gnuplot_script_file.write("replot \'"+BREW_SESSION_FILENAME+".dat\' using 1:7 title \"Lo Alarm\" with lines\n")
  gnuplot_script_file.write("pause "+str(CHARTING_INTERVAL)+"\n")
  gnuplot_script_file.write("reread\n")

#  gnuplot_script_file.write("pause 1\n")

  gnuplot_script_file.close()

  return

#write brew session data to file ####################################################
def write_gnuplot_script():
  global LAST_BREW_SESSION_TIME,DATA_TO_PLOT,NUM_DATA_POINTS,PLOT_STARTED


  if not CHARTING_ON:
    return

  from datetime import datetime

  if not PLOT_STARTED and DATA_TO_PLOT:
    from threading import Thread
    t = Thread(target=gnuplot_thread,args=())
    t.start()
    PLOT_STARTED = True
  
  if time.time() - PROGRAM_START_TIME < 60: #wait for avg temp to stabilize
    return

  if time.time() - LAST_BREW_SESSION_TIME < CHARTING_INTERVAL: #wait for interval time
    return

  if BREW_CYCLE == "Off  ":#No need to update session data if crew cycle is off
    return

  gnuplot_script_data_file = open(BREW_SESSION_FILENAME+".dat", "a")#open the brew session database

#log timestamp, current avg temp, min temp, and max temp to data file
  gnuplot_script_data_file.write(str(datetime.now().strftime("%Y-%m-%d %H:%M")) + "," + str(round(O_trending.moving_avg_temp,4)) + "," + str(round(MIN_TEMP,4)) + "," + str(round(MAX_TEMP,4)) + "," + str(round(DESIRED_TEMP,4))+ "," + str(round(MAX_HIGH_TEMP,4)) + "," + str(round(MIN_LOW_TEMP,4)) +"\n")

  gnuplot_script_data_file.close()#close the data file

  LAST_BREW_SESSION_TIME = time.time()#log time brew session data file was updated

  if NUM_DATA_POINTS < 2:
    NUM_DATA_POINTS += 1
    if NUM_DATA_POINTS > 1:
      DATA_TO_PLOT = True
      
  return

#write settings to file ########################################################
def write_settings():

  settings_file = open("bccconfig.py", "w") #overwrite existing settings file

  settings_file.write("TEMP_SCALE = '" + TEMP_SCALE + "'\n")
  settings_file.write("LAGER_TEMP = " + str(LAGER_TEMP) + "\n")
  settings_file.write("WARM_TEMP = " + str(WARM_TEMP) + "\n")
  settings_file.write("NORM_TEMP = " + str(NORM_TEMP) + "\n")
  settings_file.write("CRASH_TEMP =" + str(CRASH_TEMP) + "\n")
  settings_file.write("CLEAR_TEMP =" + str(CLEAR_TEMP) + "\n")
  settings_file.write("DESIRED_TEMP = " + str(DESIRED_TEMP) + "\n")
  settings_file.write("DWELL = " + str(DWELL) + "\n")
  settings_file.write("MAX_HIGH_TEMP = " + str(MAX_HIGH_TEMP) + "\n")
  settings_file.write("MIN_LOW_TEMP = " + str(MIN_LOW_TEMP) + "\n")
  settings_file.write("MIN_TEMP = " + str(MIN_TEMP) + "\n")
  settings_file.write("MAX_TEMP = " + str(MAX_TEMP) + "\n")
  settings_file.write("BREW_CYCLE = '" + str(BREW_CYCLE) + "'\n")
  settings_file.write("Y_PROF_ID = " + str(Y_PROF_ID) + "\n")
  settings_file.write("Y_LAB = '" + str(Y_LAB) + "'\n")
  settings_file.write("Y_NUM = '" + str(Y_NUM) + "'\n")
  settings_file.write("Y_NAME = '" + str(Y_NAME) + "'\n")
  settings_file.write("Y_STYLE = '" + str(Y_STYLE) + "'\n")
  settings_file.write("Y_DESC = '" + str(Y_DESC) + "'\n")
  settings_file.write("Y_LOW_TEMP = " + str(Y_LOW_TEMP) + "\n")
  settings_file.write("Y_HIGH_TEMP = " + str(Y_HIGH_TEMP) + "\n")
  settings_file.write("SMS_ALARM_ON = " + str(SMS_ALARM_ON) + "\n")
  settings_file.write("ALARM_SYS_ON = " + str(ALARM_SYS_ON) + "\n")
  settings_file.write("CELL_NUMBER = '" + str(CELL_NUMBER) + "'\n")
  settings_file.write("BREW_NAME = '" + str(BREW_NAME) + "'\n")
  settings_file.write("BREW_BATCH_NUM = '" + str(BREW_BATCH_NUM) + "'\n")
  settings_file.write("BREW_BATCH_SIZE = " + str(BREW_BATCH_SIZE) + "\n")
  settings_file.write("BREW_STYLE = '" + str(BREW_STYLE) + "'\n")
  settings_file.write("BREW_METHOD = '" + str(BREW_METHOD) + "'\n")
  settings_file.write("BREW_SESSION_FILENAME = '" + str(BREW_SESSION_FILENAME) + "'\n")
  settings_file.write("CHARTING_ON = " + str(CHARTING_ON) + "\n")
  settings_file.write("CHARTING_INTERVAL = " + str(CHARTING_INTERVAL) + "\n")
  settings_file.write("DATA_TO_PLOT = " + str(DATA_TO_PLOT) + "\n")

  settings_file.close()

  return

#write program start info to database##########################################
def init_database():

  from datetime import datetime

  database_file = open("database.csv", "a")

  database_file.write("bcc.py " + str(VERSION) + " started: " + str(datetime.now()) + "\n")
  database_file.write(str(BREW_NAME)+", "+str(BREW_BATCH_NUM)+", "+str(BREW_BATCH_SIZE)+", "+str(BREW_STYLE)+", "+
                      str(BREW_METHOD)+", "+str(Y_PROF_ID)+", "+str(Y_NAME)+"\n")

  database_file.close()

  return


#write current status to database###############################################
def write_database():
  global PROGRAM_START_TIME,LAST_TIME_DATABASE,DATABASE_INTERVAL,Y_PROF_ID,HEATER_ON,COOLER_ON, ALARM_SYS_ON,IS_ALARM,ALARM_HIGH_TEMP,ALARM_LOW_TEMP,ALARM_COOLER_MALFUNC,ALARM_HEATER_MALFUNC, SMS_ALARM_ON,TEMP_SCALE,BREW_CYCLE

  if time.time() - PROGRAM_START_TIME < 60: #wait for avg temp to stabilize
    return

  if BREW_CYCLE == "Off  ":#No need to update database if crew cycle is off
    return

  if time.time() - LAST_TIME_DATABASE < DATABASE_INTERVAL: #wait for database interval time to expire
    return

  from datetime import datetime

  database_file = open("database.csv", "a") #open database file to append info

  """
Line format:
column 01: date/time
column 02: current avg_temp
column 03: min temp
column 04: max temp
column 05: alarm max high
column 06: alarm min low
column 07: yeast ID
column 08: heater on
column 09: cooler on
column 10: alarm sys on
column 11: is alarm
column 12: high temp alarm
column 13: low temp alarm
column 14: cooling malfunction
column 15: heating malfunction
column 16: send sms texts
column 17: temperature scale

  """

  database_file.write(str(datetime.now()) + "," + str(BREW_CYCLE) + "," + str(round(O_trending.moving_avg_temp,4)) + "," + 
                      str(round(MIN_TEMP,4)) + "," + str(round(MAX_TEMP,4)) + "," + 
                      str(round(MIN_LOW_TEMP)) + "," + str(round(MAX_HIGH_TEMP)) + "," + str(Y_PROF_ID) + "," + 
                      str(HEATER_ON) + "," + str(COOLER_ON) + "," + str(ALARM_SYS_ON) + "," + 
                      str(IS_ALARM) + "," + str(ALARM_HIGH_TEMP) + "," + str(ALARM_LOW_TEMP) + "," + 
                      str(ALARM_COOLER_MALFUNC) + "," + str(ALARM_HEATER_MALFUNC) + "," + 
                      str(SMS_ALARM_ON) + "," + str(TEMP_SCALE) + "\n")

  database_file.close()

  LAST_TIME_DATABASE = time.time()

  return

#update current status to database###############################################
def update_database():
  global PROGRAM_START_TIME,LAST_TIME_DATABASE,DATABASE_INTERVAL,Y_PROF_ID,HEATER_ON,COOLER_ON, ALARM_SYS_ON,IS_ALARM,ALARM_HIGH_TEMP,ALARM_LOW_TEMP,ALARM_COOLER_MALFUNC,ALARM_HEATER_MALFUNC, SMS_ALARM_ON,TEMP_SCALE,BREW_CYCLE

  from datetime import datetime

  if time.time() - PROGRAM_START_TIME < 60: #wait for avg temp to stabilize
    return

  if BREW_CYCLE == "Off  ":#No need to update database if crew cycle is off
    return


  database_file = open("database.csv", "a") #open database file to append info

  """
Line format:
column 01: date/time
column 02: current avg_temp
column 03: min temp
column 04: max temp
column 05: alarm max high
column 06: alarm min low
column 07: yeast ID
column 08: heater on
column 09: cooler on
column 10: alarm sys on
column 11: is alarm
column 12: high temp alarm
column 13: low temp alarm
column 14: cooling malfunction
column 15: heating malfunction
column 16: send sms texts
column 17: temperature scale

  """

  database_file.write(str(datetime.now()) + "," + str(BREW_CYCLE) + "," + str(round(O_trending.moving_avg_temp,4)) + "," + 
                      str(round(MIN_TEMP,4)) + "," + str(round(MAX_TEMP,4)) + "," + 
                      str(round(MIN_LOW_TEMP)) + "," + str(round(MAX_HIGH_TEMP)) + "," + str(Y_PROF_ID) + "," + 
                      str(HEATER_ON) + "," + str(COOLER_ON) + "," + str(ALARM_SYS_ON) + "," + 
                      str(IS_ALARM) + "," + str(ALARM_HIGH_TEMP) + "," + str(ALARM_LOW_TEMP) + "," + 
                      str(ALARM_COOLER_MALFUNC) + "," + str(ALARM_HEATER_MALFUNC) + "," + 
                      str(SMS_ALARM_ON) + "," + str(TEMP_SCALE) + "\n")

  database_file.close()

  return


# gnuplot_thread() #######################################################
def gnuplot_thread():
  global DATA_TO_PLOT

  from os import system

  while not DATA_TO_PLOT:
    time.sleep(60)

  system( '/usr/bin/gnuplot \''+BREW_SESSION_FILENAME+'.gp\'')

  return

########### MAIN PROGRAM STARTS HERE #####################################
self_test()

draw_screen()

O_trending = Trend()
move_average = O_trending.move_average

#write program start info to database
init_database()

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

    #write to database file
    write_database()

    #write the brew session data to the data file
    write_gnuplot_script()

    #update brew session gnuplot script
    update_gnuplot_script()

    #15 second delay/indicate the program is running/check for user input
    delay_loop()

exit(0) #should never get here but just in case exit



