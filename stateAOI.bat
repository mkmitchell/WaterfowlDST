@ECHO OFF
::[Supply, demand, species proportion, protected lands, habitat proportion, urban, data check, zip it]
python runModel.py -w "C:\Proc\Mike\JVDST" -g ModelReady.gdb -l CONUS_wetlands aoiWetland.json -p PADUS2_0Fee -n NCED_Polygons -k SAkcal.csv -d Demand9Species_Merged -e MarshVector marsh.csv Impoundments Impoundments.csv -a state STATE_NAME -b WBDHU12 -u HUC12 name -r SouthMSUrbanDissolve -f ModelOutputFieldDictionary.csv