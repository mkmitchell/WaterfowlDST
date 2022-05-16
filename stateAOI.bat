@ECHO OFF
::[Energy supply, Energy demand, Species proportion, protected lands, habitat proportion, urban, full model, data check, merge all, zip]
python runModel.py -w "C:\Proc\Mike\JVDST" -g ModelReady.gdb -l CONUS_wetlands aoiWetland.json -p PADUS2_0Fee -n NCED_Polygons -k SAkcal.csv -d Demand9Species_Merged -e MarshVector marsh.csv Impoundments Impoundments.csv -a state3 STUSPS10 -b WBDHU12 -u HUC12 name -r nlcd2019Albers -f ModelOutputFieldDictionary.csv -c 0 -z 0 0 0 0 0 0 1 1 1 1