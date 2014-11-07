bcc
===

Beer brew chamber temperature contoller code for Beaglebone Black

License: http://opensource.org/licenses/GPL-3.0

A project of mine I want to share with the maker/hacker community and fellow homebrewers.

http://mybbbprojects.blogspot.com/2014/07/introduction.html

PROJECT GOALS

THE BARE BONES REQUIREMENTS

    (*)Monitor ambient brew chamber air temperature
    (*)Turn on heating if needed
    (*)Turn on cooling if needed

SELECTING AND AUTOMATING THE PROCESS

    ( )Ability to select different fermentation processes depending on what we are making
    ( )Automate the fermentation process
        (*)Warmer start temperature to quickly optimize yeast colony size
        ( )Gradual cooling to optimum fermentation temperatures
        (*)Cold crash cycle when ferment is complete (requires a freezer)
        (*)Lager cycle if needed for style of beer (requires a freezer)
    ( )Network access (SSH, WWW and/or VNC for GUI) to the controller
        ( )Private access for control of the process
        ( )Public access for monitoring the process 
        (*)SSH
	(*)VNC
    (*)Alarm system sends texts/emails/tweets etc. 
    (*)CSV database to track history/store yeast statistics etc.
    (*)Plot charts of brew session data

OTHER THINGS TO MONITOR

    ( )Monitor fermentation vessel temperature
        ( )Chart vessel/chamber temperature differential
    ( )Web cam for visual monitoring
    ( )Monitor fluid level in airlock system
    ( )CO2 off gassing
        ( )Monitor rate of fermentation
        ( )Determine when fermentation is complete
    ( )Monitor power consumption
    ( )Monitor keg pressures
    ( )Monitor external/room temperature 
    ( )Monitor humidity (still not sure on this)

LOCAL INPUT GUI DEVICE

    ( )Local LCD touchscreen GUI 
       doubles the expense but gives a nice 
       professional finishing touch
