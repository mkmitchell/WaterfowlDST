"""
Waterfowl model header at the top.
"""
class Waterfowlmodel:
  """Class to store waterfowl model parameters."""
  def __init__(self, aoi):
    """Create a waterfowl model object by providing an area of interst (aoi)."""
    self.aoi = aoi

  def getAOI(self):
    """
    :return: The model area of interest
    :rtype: str
    """
    return self.aoi 