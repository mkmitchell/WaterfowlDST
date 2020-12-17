"""
zipUp
===============
zipUp zips up a geodatabase for the purpose of uploading it to agol.
"""
# import modules
import shutil, os
from datetime import datetime
  
def zipUp(base = r'C:\Users\jskillman\Ducks Unlimited Incorporated\GIS Department - ABDU DST and more!\GIS\Output', 
  fldr = r'C:\Users\jskillman\Ducks Unlimited Incorporated\GIS Department - ABDU DST and more!\GIS\Output\_12072020\SouthAtlantic_output'):
  """
  Zips up the geodatabase for upload.
  
  :param base: The path to the base folder in which all output db are held. 
  :type table: str
  :param fldr: The folder that contains the geodatabase to zip up. Will zip up all items in that folder, so make sure only the gdb is there.
  : type fldr: str
  """
  # make new output folder in the GIS output folder
  newfolder = '_{}'.format(datetime.now().strftime('%d_%m_%Y'))
  newpath = os.path.join(base,newfolder)

  if not os.path.exists(newpath):
    os.makedirs(newpath)

  # name of new zipfile
  myzipfile = os.path.join(newpath, 'ABDU_DST_output')
  # zip it.
  shutil.make_archive(myzipfile, 'zip', fldr)