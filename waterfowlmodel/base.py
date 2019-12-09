"""
Module Waterfowl
================
Defines Waterfowlmodel class which is initialized by supplying an area of interest shapfile, wetland shapefile, kilocalorie by habitat type table, and the table linking the wetland shapefile to the kcal table.
"""
import os, sys, getopt, datetime, logging, arcpy
from arcpy import env

class Waterfowlmodel:
  """Class to store waterfowl model parameters."""
  def __init__(self, aoi, wetland, kcalTable, crosswalk, demand, scratch):
    """
    Creates a waterfowl model object.
    
    :param aoi: Area of interest shapefile
    :type aoi: str
    :param wetland: National Wetlands Inventory shapefile
    :type wetland: str
    :param kcalTable: CSV file containing two columns [habitat type, kilocalorie value by acre]
    :type kcalTable: str
    :param crosswalk: CSV file relating wetland habitat types to kcal csv table
    :type crosswalk: str
    :param demand: NAWCA stepdown DUD objectives
    :type demand: str
    :param scratch: Scratch geodatabase location
    :type scratch: str
    """
    self.aoi = aoi
    self.wetland = wetland
    self.kcalTbl = kcalTable
    self.crossTbl = crosswalk
    self.demand = demand
    self.scratch = scratch
    env.workspace = scratch

  def clipStuff(self):
    if arcpy.Exists(os.path.join(os.path.dirname(self.scratch),"aoiWetland.shp")):
      print('Already have nwi clipped with aoi')
      logging.info('Already have nwi clipped with aoi')
    else:
      arcpy.Clip_analysis(self.wetland, self.aoi, os.path.join(os.path.dirname(self.scratch),"aoiWetland.shp"))
      logging.info("Clipping features")
    self.wetland = os.path.join(os.path.dirname(self.scratch),"aoiWetland.shp")

  def prepEnergy(self, habtype = 'ATTRIBUTE'):
    """
    Returns habitat energy availability feature with a new field [avalNrgy] calculated from joining crosswalk table to habitat value and assigning energy.

    :param habtype: Habitat type field
    :type habtype: str
    :return: Available habitat feature
    :rtype: str
    """
    print(self.wetland)
    if len(arcpy.ListFields(self.wetland,'avalNrgy'))>0:
      print("Energy field exists")
    else:
      print("Adding energy field")
      arcpy.AddField_management(self.wetland, 'avalNrgy', "DOUBLE", 9, "", "", "AvailableEnergy")
    
    arcpy.JoinField_management(self.wetland, habtype, self.crossTbl, 'fromHabitat', ['fromHabitat', 'toHabitat'])
    arcpy.CalculateField_management(self.wetland, 'avalNrgy', "!toHabitat!", "PYTHON3")
    return "energy ready!"

  def dstOutout(self):
    """
    Runs energy difference between NAWCA stepdown objectives and available habitat.

    :return: Shapefile containing model results at the county level
    :rtype: str
    """
    return "outputFile"

  def bin(self, aggData, aggCol, bins):
    """
    Calculates proportional sum aggregate based on area within specified columns of a given dataset to features from another dataset.

    :param aggData: Dataset that contains information to be aggregated spatially
    :type aggData: str
    :param aggCol: Columns within aggData that need to have the sum aggregate function applied to them
    :type aggCol: str
    :param bins: Spatial dataset used as the aggregation feature.  Data will be binned to the features within this dataset.
    :type bins: str
    :return: Spatial Sum aggregate of aggData within supplied bins
    :rtype:  str
    """
    return "binned file"