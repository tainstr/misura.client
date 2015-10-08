.. include:: substitutions.txt

Heating Microscope HSM
======================

To open the HSM controls, you have to select HSM in the selection window that apperas after having logged in.

HSM window is made of three main parts:

- `Camera Window`_
- `Data Plot`_
- `Data Table`_
- `Story board`_
- `Test Configuration panel`_



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

[TBD]


Data Table
----------

The *Data Table* is a table that contains plotted data.

To view it, click on *Measure* menu and select *Data Plot*.

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
- `Thermal Cycle`_
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
- [TBD]


-------------
Thermal Cycle
-------------

The Thermal Cycle tab contains the controls to setup the wanted thermal cycle.

To set a thermal cycle, you have to insert your desired values in the given table. Each row of this table represent a segment of the cycle. A segment can be:

- a temperature ramp
- a checkpoint (wait until a given temperature is reached or a given timeout has expired)
- a movement (open or close the furnace)
- a control transition (change which thermocouple is used to control the cycle)

To add a temperature ramp to the table, you have to right click on a row and select *Insert point*. Then, you can double click on the values you want to change: typically you set an heating rate and a temperature: duration and time will be automatically calculated based on the previous row.

To add a checkpoint, right click and select *Insert checkpoint*. A dialog will show up, where you'll be able insert the desired temperature and timeout.

To add a movement, right click and select *Insert movement*. A dialog will show up, and you'll be able to select a *Open* or *Close* furnace movement.

To add a control transition, right click and select *Insert control transition*. A dialog will show up, and you'll be able to select to which of the thermocouples move the control and how fast.

You can delete a line with a right click on the line to be deleted and select *Remove current line*.

The *Stop after thermal cycle* flag defines wether the acquisition should stop or not, when the thermal cycle reaches its end. If not, the acquisition will have to be stopped manually.

In the lower part of the tab a graphical representation of the cycle is displyed.


-------
Samples
-------

[TBD]

-------
Results
-------

The *Results* tab shows is a tree that contains all the data being acquired, and allows you to plot them in the `Data Plot`_.

[TBD]