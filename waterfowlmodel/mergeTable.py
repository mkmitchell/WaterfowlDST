"""
Module MergeTable
================
Defines Merge Table class which is initialized by supplying a geodatabase and wildcard that the tables to be merged start with
"""
import os, sys, getopt, datetime, logging, arcpy
from arcpy import env

class MergeTable:
  """Class to merge NWI Tables."""
  def __init__(self, gdb, wild):
      print('Merging tables in', gdb)