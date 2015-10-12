.. include:: substitutions.txt

Installation
==================================

This document describes the installation and quick start of |m4| software. 

==============================
Prerequisites
==============================

* 1GB of free hard disk storage
* 500MB of free RAM. For typical operating system use, we advise 2GB of system RAM for GNU/Linux and 4GB of system RAM for |win|.
* 2Ghz, dual core processor


=======
|win|
=======
|m4| for |win| XP / Vista / 7 / 8 can be downloaded as a compressed zip file, containing executable files, libraries and data.

Precompiled executables and example data packages are available on |m| public repository: `https://github.com/tainstr/misura.client/releases`_

1. Extract all contents of the zip file to ``C:\misura``. 
	.. tip:: Experienced users can choose their preferred location. Please consider that placing the application on external hard-drives or slow storage devices can significantly affect startup time.
2. Browse to ``C:\misura``. You will find many files: locate the 3 main executable files, ``browser.exe``, ``acquisition.exe``, ``graphics.exe``.
3. For each executable file, right click on it and select "Create link". A new file will be created each time (E.g.: ``C:\misura\browser.exe - link``). 
4. Copy or move the newly created link files to your Desktop, in order to find them more easily.


----------
Upgrading
----------
Upgrading involves making a backup copy of the old application folder and installing the upgraded version over the old location.

	1. Rename ``C:\misura`` to ``C:\misura_backup``.
	2. Create an empty ``C:\misura`` folder and repeat installation steps from previous section.

========
|u|
========
|m4| for |ults| GNU/Linux operative system does not offer executable files. The application is run directly from the |py| source code. Thus, it requires the installation of the full development environment and the download of the entire source code from the version control repository.

.. _https://github.com/tainstr/misura.client/releases: https://github.com/tainstr/misura.client/releases