#!/bin/sh

for((i=0;i<=10000;i++))
do
  ls -tlhr static/*csv | awk '{ print $NF; }'  > filename.list
  while read filename
  do

     egrep -v "N" $filename > "$filename".bak
     cp -rf "$filename".bak $filename 

  done < filename.list
 
  nohup python temp.py 1>out.1 2>err.1 &
  sleep 1800
done
