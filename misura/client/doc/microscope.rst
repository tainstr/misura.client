.. include:: substitutions.txt

Heating Microscope HSM
======================

To open the HSM controls, you have to select HSM in the selection window that apperas after having logged in.

HSM window is made of these main parts:

- `Buttons bar`_
- `Camera Window`_
- `Data Plot`_
- `Data Table`_
- `Story board`_
- `Test Configuration panel`_


Buttons bar
-----------

The button bar in the upper side of the main window has four buttons:

- *New*: reinitialize the current instrument for a new test
- *Start*: starts a new `Live Acquisition`_
- *Stop*: stops the current `Live Acquisition`_
- *Cool*: stops the thermal cycle, but continue acquisition.

.. _Live Acquisition: live.html

Camera window
-------------

The Camera window allows you to control the microscope's camera. A vertical slider on the left allows you to move its position along the vertical direction.

By right-clicking on the window, you gain access to a menu with a series of functionality:

- **Stream** is a flag that turns on/off the camera streaming.
- **Fit view** makes the camera image resized so to fit the window size
- **Configure** opens the camera configuration window
- **Simulation** simulates the image analysis that would be made during the test
- **Imaging** submenu allows to tune these imaging camera paroperties:
    - *Exposure*
    - *Contrast*
    - *Brightness*
    - *Gamma*
    - *Gain*
- **Analysis** submenu
- **Motion** submenu allows to control vertical position.
- **Save Frame** allows to save currently displayed samples details.
- **SampleN** submenu allows to access some configuration details of the Nth sample
    - *Configure* opens sample configuration dialog
    - *Black/white levelling*
    - *Adaptative threshold*
    - *Dynamic regions*



Data Plot
---------

Data plot allows you to plot acquired data.

To view it, click on Measure menu and select *Data Plot*.

To access the visualization's tweaks, you can right click on an element of the plot to get its options menu:

- *Axis* allows you to change what axis measures are plotted towards.
- *Curves* allows you to select what curves to plot.
- *View* allows you to select if you want data to be plotted by *temperature* or by *time*.
- *Reset* rebuilds the data plot
- *Update* forces a reload of data.
- *Properties* allows you to set behavioural features of the clicked element
- *Formatting* allows you to set appearance features of the clicked element
- *Zoom* changes the zoom level
- *Preious / Next Page* changes the currently visualized page.
- *Full Screen* toggles fullscreen mode.
- *Updates* allows you to change the update frequency of th page.
- *Antialias* toggles antialias
- *Export* allows you to export the current page to a pdf

Other visualization options are accesible via the Results_ tab.


Data Table
----------

The *Data Table* is a table that contains plotted data.

To view it, click on *Measure* menu and select *Data Table*.

The menu that appears by right clicking the header, allows you to export data in *csv* format and to hide or show columns.


Story board
-----------

The Story Board panel, located by default in the lower part of the main window, shows the list of the samples' profiles being acquired.

It's made out of:

- a slider to move through the list of images
- a dropdown box that allows you to select the currently displayed sample
- the list of the current sample's profile's images



Test Configuration panel
------------------------

The Test Configuration panel, located in the right part of the main window, allows you to setup the test.

It's composed of a series of tab:

- Status_
- Measure_
- `Thermal Cycle Designer`_
- Samples_
- Results_


------
Status
------

Status tab is a summary of what's happening to the instrument.

-------
Measure
-------

This tab contains:

- *Configuration preset*: a combo that allows you to load a previously saved configuration. *Save* and *Del* buttons respectively save and delete currently selected preset.
- *Name*: the name to give to the test.
- *Maximum test duration*: defines the amount of passed time that will cause the end of the test, even if the thermal cycle is not completed (-1 removes this timeout)
- *Stop after thermal cycle*: when set, the acquisition will stop when the thermal cycle is over. If not set, the acquisition will go on until the operator won't stop it manually.
- *Operator*: the operator running the test
- *Type*: the type of test. Only *Standard* is supported to date
- *Start at* is the time and date the test was started
- *Number of samples*: sets the number of samples to analyze (can be from 1 to 8)
- *Kiln position before acquisition*: the position where the kiln will be placed right before the start of the acquisition
- *Kiln position after acquisition*: the position where the kiln will be placed after the end of the acquisition
- *End status*: displays the reason of the acquisition's termination


.. include:: components/thermal_cycle.rst


-------
Samples
-------

Every sample has its own tab, named Sample0, Sample1, ...

Each tab contains the details of its sample:

- *Configuration preset* is the currentrly loaded preset. You can change it, save it if you make any change, and delete it.
- *Name* is the name of the sample
- *Temperature* is the current sample temperature
- *Initial sample dimension* is the size of the specimen, before the start of the test
- *Record frames* defines wether tha raw frame of the sample should be saved or not
- *Record profiles* defines wether the sample profiles have to be saved or not
- *Border angle* is the angle of currently detected border
- *Total displacement* is the current displacement from initial position

-------
Results
-------

The *Results* tab contains another series of tabs, which are:

- *Data Tab*: a tree that contains all plottable data to allow you to perform operations over it.
- *Properties* and *Formatting*: are the equivalent of Properties and Formatting on the right click menu of the `Data Plot`_. Operations are applied on the object selected in the Objects tab or on the plot.
- *Objects* is a 1 to 1 representation of the plot; it allows to select objects to perform operations in other contexts.
- *Console* is the Veusz_ output console.

.. _Veusz: http://home.gna.org/veusz/
