bcc
===

Beer brew chamber temperature contoller code for Beaglebone Black

A project of mine I want to share with the maker/hacker communityllow homebrewers.

http://mybbbprojects.blogspot.com/2014/07/introduction.html

PROJECT GOALS

THE BARE BONES REQUIREMENTS

    Monitor ambient brew chamber air temperature
    Turn on heating if needed
    Turn on cooling if needed

SELECTING AND AUTOMATING THE PROCESS

    Ability to select different fermentation processes depending on what we are making
    Automate the fermentation process
        warmer start temperature to quickly optimize yeast colony size
        gradual cooling to optimum fermentation temperatures
        cold crash cycle when ferment is complete (requires a freezer)
        lager cycle if needed for style of beer (requires a freezer)
    Network access (SSH, WWW and/or VNC for GUI) to the controller
        Private access for control of the process
        Public access for monitoring the process 
    Alarm system sends texts/emails/tweets etc. 
    MySQL database to track history/store yeast statistics etc.

OTHER THINGS TO MONITOR

    Monitor fermentation vessel temperature
        Chart vessel/chamber temperature differential
    Web cam for visual monitoring
    CO2 off gassing
        Monitor rate of fermentation
        Determine when fermentation is complete
    Monitor  power consumption
    Monitor keg pressures
    Monitor external/room temperature 
    Monitor humidity (still not sure on this)

LOCAL INPUT GUI DEVICE

    Local LCD touchscreen GUI (doubles the expense but gives a nice professional finishing touch)
