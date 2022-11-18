Waterfowl Decision Support Tool Documentation
=============================================

This waterfowl model has been created to support east coast joint venture waterfowl planning.

We've experienced many difficulties using only arcpy for the workflow.  Sometimes we got around this by converting data
to raster, sometimes we incorporated numpy or geopandas, and othertimes multiprocessing helped.  When adding in an element
that wasn't previously there different problems.  Examples include simple arcpy tools failing to operate when incorprating
multiprocessing.  Dissolve SUM was adding an extra '0' to a small subset of fields at one point and swithing to MEAN fixed it.

After updating ArcPro geopandas failed to work or install because of conflicts.  This code was designed to work with 2.7.x and geopandas installed.

This codebase will slowly change as time allows.  The goal is to make it more modular and as this happens arcpy will be
stripped out and replaced with geopandas, rasterio, or other similar open source libraries.

Code documentation - https://mkmitchell.github.io/WaterfowlDST/runModel.html#runmodel

