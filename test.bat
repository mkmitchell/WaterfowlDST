@ECHO OFF
: python runModel.py -w "D:\GIS\scratch\dst" -g ModelReady.gdb -l testnwi aoiWetland.json -k kcal.csv -d EnergyDemand  -a testJV -b HUC12

python D:\bitbucket_rename\abdu_dst\runModel.py -w "C:\Users\jskillman\Ducks Unlimited Incorporated\GIS Department - ABDU DST and more!\GIS\ModelReady" -g ModelReady.gdb -l testnwi aoiWetland.json -k kcal.csv -d EnergyDemand  -a testJV -b huc12
