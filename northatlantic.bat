@ECHO OFF
::[Supply, Demand, protected lands, habitat proportion, weighted mean, data check, zip it]
python runModel.py -w "C:\Proc\Mike\JVDST" -g ModelReady.gdb -l CONUS_wetlands aoiWetland.json -p PADUS2_0Fee -n NCED_Polygons -k NAkcal.csv -d Demand9Species_Merged -e MarshVector marsh.csv Impoundments Impoundments.csv -a NorthAtlantic -b WBDHU12 -u HUC12 name -r UrbanNADissolve -f ModelOutputFieldDictionary.csv -z 0 0 0 0 0 0 1 1 1 1
