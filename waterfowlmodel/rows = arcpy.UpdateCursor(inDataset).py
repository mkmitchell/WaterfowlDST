    rows = arcpy.UpdateCursor(inDataset)
    for row in rows:
      if row.getValue('CLASS') == '' or row.isNull('CLASS') or row.getValue('CLASS') == None:
        for key,value in dataDict.items():
            if row.getValue(curclass).replace(',', '') in value:
              row.setValue('CLASS', key)
              rows.updateRow(row)
      else:
            continue

    with arcpy.da.UpdateCursor(inDataset, 'CLASS') as cursor:
        for row in cursor:
            if row[0].strip() == '' or row[0] is None:
                if row[0] in dataDict:
                    row[0] = dataDict[row[0]]
                    cursor.updateRow(row)
            else:
                continue
            
