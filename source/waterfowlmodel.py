"""
Module Waterfowl
================
Defines Waterfowlmodel class which is initialized by supplying an area of interest shapfile, wetland shapefile, kilocalorie by habitat type table, and the table linking the wetland shapefile to the kcal table.
"""
class Waterfowlmodel:
  """Class to store waterfowl model parameters."""
  def __init__(self, aoi, nwi, kcalTable, crosswalk):
    """
    Creates a waterfowl model object.
    
    :param aoi: Area of interest layer
    :type aoi: str
    :param wetlands: National Wetlands Inventory and Canada Wetlands Inventory layers
    :type wetlands: str
    :param kcalTable: CSV file containing two columns [habitat type, kilocalorie value by acre]
    :type kcalTable: str
    :param crosswalk: CSV file relating wetland habitat types to kcal csv table
    :type crosswalk: str
    """
    self.aoi = aoi
    self.wetlands = nwi
    self.kcalTbl = kcalTable
    self.crossTbl = crosswalk

  def getAOI(self):
    """
    Returns the area of interest.  For testing purposes

    :return: The model area of interest
    :rtype: str
    """
    return self.aoi

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
