.. include:: ../substitutions.txt
.. |smp| replace:: ``Vertical Dilatometer Sample File 1.h5``
.. |smprep| replace:: ``Vertical Dilatometer Sample Report 1.pdf``
.. |instr| replace:: vertical
.. |instrn| replace:: Vertical Dilatometer

Quick Start: Browsing a Vertical Dilatometer file 
========================================

This Demo will guide you through the data analysis of an Vertical Dilatometer output file. 

.. include:: quickstart/opening.txt
.. include:: quickstart/config.txt

=================================
Interacting with the Data Plot
=================================

The :ref:`navigator` tree is the gate to the most important actions you can perform on the data plot. 

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

