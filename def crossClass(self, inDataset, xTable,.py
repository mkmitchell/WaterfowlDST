def crossClass(self, inDataset, xTable, curclass):
    """
    Joining large datasets is way too slow and may crash.  Iterating with a check for null will make sure all data is filled.

    :param inDataset: Feature to be updated with a new 'CLASS' field
    :type inDataset: str
    :param xTable: Location of csv or json file with two columns, from class and to class
    :type xTable: str
    :param curclass: Field that lists current class within inDataset
    :type curclass: str.
    """
    logging.info("Calculating habitat")
    print(inDataset)
    print(xTable)
    if len(arcpy.ListFields(inDataset,'CLASS'))>0:
      print('Already have CLASS field')
    else:
      print('Add CLASS habitat')
      arcpy.AddField_management(inDataset, 'CLASS', "TEXT", 50)
    # Read data from file:
    #filename, file_extension = os.path.splitext(xTable)
    file_extension = os.path.splitext(xTable)[-1].lower()
    if file_extension == ".json":
      dataDict = json.load(open(xTable))
    else:
      with open(xTable, mode='r') as infile:
        reader = csv.reader(infile)
        dataDict = {rows[0]:rows[1].split(',') for rows in reader}

    """    rows = arcpy.UpdateCursor(inDataset)
    for row in rows:
      if row.getValue('CLASS') == '' or row.isNull('CLASS') or row.getValue('CLASS') == None:
        for key,value in dataDict.items():
            if row.getValue(curclass).replace(',', '') in value:
              row.setValue('CLASS', key)
              rows.updateRow(row)
      else:
            continue"""

    with arcpy.da.UpdateCursor(inDataset, [curclass, 'CLASS']) as cursor:
      for row in cursor:
        if row[1] is None or row[1].strip() == '':
          if row[0] in dataDict:
            row[1] = dataDict[row[0]]
            cursor.updateRow(row)
        else:
          continue


crossClass(self, inDataset, xTable, curclass)