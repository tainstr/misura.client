.. include:: ../substitutions.txt
.. |smp| replace:: ``Vertical Dilatometer Sample File 1.h5``
.. |smprep| replace:: ``Vertical Dilatometer Sample Report 1.pdf``

Quick Start: Browsing a Vertical Dilatometer file 
========================================

This Demo will guide you through the data analysis of an Vertical Dilatometer output file. 

In order to follow the tutorial you should:
	
* Download and Install Misura\ |trade|.
* Get the sample file |smp| and save it to a known location (eg: your Desktop)
* Have successfully followed the guide :doc:`quickstart_hsm`.

=========================
Opening the output file
=========================

1. Run ``archive.exe`` application from the folder where you extracted |m|, or run the link you created on your desktop.
2. In the **Recent data sources** window, under the first column **Recent files**, click on **Open** button.
3. Browse to the location where you downloaded |smp|, select and open it.
4. The loading process will start. If the file is considerably big (several GB) or located on network or slow storage drive, it may take several seconds to open.
5. The file is displayed on a new tab, on the right of the **Databases** tab.

The test file tab is divided in three areas:

* A menu bar and tools bar in the upper part of the window
* A right area called **Test Configuration**. It is divided in at least 4 vertical tabs: **Measure**, **Thermal Cycle**, **Sample0** and **Results**.
* A central area displaying movable and resizable sub-windows, where you see the **Data Plot** window.

=================================
Test Configuration and Data
=================================
The most relevant configuration options used for the test run and output results are displayed in the right **Test Configuration** area. 

---------------------
Measure overview
---------------------
The first **Measure** tab contains the list of options regarding the test run. 

Detect the following:
	
* **Name**: Name of the test run, set by the operator anytime before the end of the test.
* **Operator**: the login name used by the operator who started the test.
* **Type**: The type of the test (usually ``Standard`` or ``Calibration``).
* **Elapsed time**: the total duration of the test.


---------------------
Thermal cycle
---------------------

This tab contains a table with points defining the thermal cycle and a graph with a cartesian representation. 

The graph displays two curves: the red line is the setpoint temperature; the blue line is the heating rate. 

If you cannot see the axes and their labels, enlarge the application window and the Test Configuration area. 

---------------------
Sample data
---------------------

Most relevant data in the Sample0 tab are:
	
* **Name**: if set, the name the operator gave to this specific sample. It is mainly useful for multi-sample measurement.
* **Initial sample dimension**: the operator must set this value to the initial sample length, measured with another instrument (eg: a digital micrometer).
* **Record frames/profiles**: did the operator required full frames and (x,y) sample profiles to be recorded onto the output file? They are usually turned off. 

You can ignore *Border angle, Motion start, Total displacement, Cumulative error* options an all their nested options, as they are only useful during live acquisition. 


---------------------
Results
---------------------
The Results tab displays the Navigator tree component. It is the tree of recorded datasets (curves), organized by groups. Each group represents a parts of the instrument or of the measurement. 

For example:
	
* **vertical** represents the Vertical Dilatometer instruments itself. It generates no datasets, but contains one sample (**sample0**).
* **kiln** represents the furnace, and contains datasets regarding temperature control (T, temperature; S, setpoint; P, power; etc).

We will see it in detail in next sections, as it is the most powerful and versatile component of the interface.


=================================
Interacting with the Data Plot
=================================

The Navigator tree is the gate to the most important actions you can perform on the data plot. 

In order to plot one more dataset (for example the temperature setpoint):
	
1. Right-click on the dataset you wish to plot on the Navigator tree (``/kiln/S``).
2. Select the **Plot** action from the context menu.
	
The same apply for removing a dataset and all its related objects from the plot. 
The Plot action will be checked if the curve is visible, unchecked if not visibile.

The setpoint curve plot is now referred to its own axis labelled *S (°C)*. 
To better compare temperature and setpoint, it is useful to refer the setpoint plot to the temperature axis:

1. Right-click on the setpoint curve on the Data Plot window. Select **Properties** from the context menu. 
2. A new dialog window opens, listing all the properties of the plotted curve. Search for the bold **Y axis** entry.
3. Change **Y axis** from **ax:S** to **ax:T**. The curve will be immediately referred to the *T (°C)* axis.

The *S (°C)* axis loses its scale (it's now from 0 to 1). It's no longer useful, so you can hide it:
1. Right-click on the *S (°C)* axis, select **Properties**.
2. The first entry is **Hide**. Check the checkbox. The axis disappears.

You can freely move any axis by clicking on it and dragging.

---------------------------------------------------
Viewing dilatation as Percentile
---------------------------------------------------
The ``/vertical/sample0/d`` dataset represents dilatation. 
It is recorded in microns, but is frequently useful to analyze it as a percentile of the total initial length of the sample.
The initial length was measured with a manual digital micrometer, and set before starting the test.

Follow these steps to convert the curve to percentile:

1. Locate the ``d`` (``/vertical/sample0/d``) element in the Navigator tree under Results tab.
2. Right-click and select **Percentile**.
3. A dialog will appear. Click **Apply**. 
4. A new temporary label in the dialog confirms the dataset was created (Done). Click **Close**.
5. If the curve is currently plotted, you immediately view the effect in the graph.
	
It may happen that the operator forget to measure the sample, or inserts a wrong initial dimension. 
If the thermal treatment modify the structure of your material, the test must be repeated. 
In case you are able to recover the correct intial dimension, or you are confident that you can measure it after the test run,
you can change its value.

1. Locate the ``d`` element in the Navigator tree.
2. Right-click and select **Set Initial Dimension**.
3. Insert the correct value in **Initial dimension value**.
4. De-select *OR, automatic calculation based on first points* checkbox.
5. Click **Apply** then **Close**. 

If the curve is currently plotted in percentile, you will se the axis scale changing accordingly to the new initial dimension set.

---------------------------------------------------
Evaluating the Coefficient of Expansion
---------------------------------------------------
The coefficient of expansion is calculated from the ``d`` dataset, the initial dimension and the temperature. 
To create the coefficient curve:

1. Locate the ``d`` element in the Navigator tree.
2. Right-click and select **Linear Coefficient**.
3. Click **Apply** and **Close**.
4. The Navigator tree is updated. The ``d`` element now has a child: *Coefficient(T,d)*. This is the coefficient of expansion.
5. Plot the coefficient dataset using its context menu.

The curve will be referred to a new axis *Coeff(50)*. The number 50 in the label means the coefficient was calculated starting from 50°C. 
The scale of the axis will be around 10\ :sup:`-6` - 10\ :sup:`-5`. You can rescale the axis to a more comfortable multiplier:

1. Right-click on the *Coeff(50)* axis. Select **Properties** action.
2. Locate the **Scale** entry and set it to 1e6. 

Now the scale of the axis should go from 2.5 to 12.5, where the multiplier is 10\ :sup:`-6`. 

