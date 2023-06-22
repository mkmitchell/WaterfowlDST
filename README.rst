Waterfowl Decision Support Tool Documentation
=============================================

This waterfowl model has been created to support east coast joint venture waterfowl planning.

We've experienced many difficulties using only arcpy for the workflow.  Sometimes we got around this by converting data
to raster, sometimes we incorporated numpy or geopandas, and othertimes multiprocessing helped.

After updating ArcPro geopandas failed to work or install because of conflicts.  This code was designed to work with ArcPro 2.7.x and geopandas installed.

This codebase will slowly change as time allows.  Future goals are to make it more modular and incorporate land use change and climate change scenarios.

Code documentation - https://mkmitchell.github.io/WaterfowlDST/runModel.html#runmodel

