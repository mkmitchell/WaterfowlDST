"""
Module Dataset
================
Defines Dataset class which is initialized by supplying habitat and the crosswalk table.
"""
import os, sys, getopt, datetime, logging, arcpy
from arcpy import env

class Dataset:
  """Class to store egs model parameters."""
  def __init__(self, inData, scratch, crosswalk = None):
    """
    Creates a EGS model object.
    
    :param inData: Dataset input
    :type inData: str
    :param crosswalk: CSV file relating habitat types
    :type crosswalk: str
    :param scratch: Scratch geodatabase location
    :type scratch: str
    """
    self.inData = inData
    self.crosswalk = crosswalk
    self.scratch = scratch
    env.workspace = scratch
