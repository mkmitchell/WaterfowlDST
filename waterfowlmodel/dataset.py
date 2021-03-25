"""
Module Dataset
================
Defines Dataset class which is initialized by supplying habitat and the crosswalk table.  It's used for organizing spatial datasets.
"""
import os, sys, getopt, datetime, logging, arcpy
from arcpy import env

class Dataset:
  """
  Dataset class 
  
  This creates a model object to store parameters for organizational purposes.

  :param inData: Dataset input
  :type inData: str
  :param scratch: Scratch geodatabase location
  :type scratch: str    
  :param crosswalk: CSV file relating input habitat types to ABDU habitat types
  :type crosswalk: str
  """
  def __init__(self, inData, scratch, crosswalk = None):
    self.inData = inData
    self.crosswalk = crosswalk
    self.scratch = scratch
    env.workspace = scratch
