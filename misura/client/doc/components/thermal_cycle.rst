-------------
Thermal Cycle
-------------

The Thermal Cycle designer contains the controls to setup the wanted thermal cycle.

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