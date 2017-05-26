#!/bin/sh

FILENAME=$1

awk -F ',' 'BEGIN{

  print "$(function() {";
  print "Morris.Area({";
  print "element: \047morris-area-chart\047,";
  print "data: [{";

}{
  if(NR%10==0)
  {
  aa=strftime("%Y-%m-%d",$1)
  print "period: \047"aa"\047,";
  print "price: \047"$2"\047,";
  print "}, {";
  }
}END{


  aa=strftime("%Y-%m-%d",$1)
  print "period: \047"aa"\047,";
  print "price: \047"$2"\047,";
  print "}],";

  print "xkey: \047period\047,";
  print "ykeys: [\047price\047],";
  print "labels: [\047price\047],";
  print "pointSize: 2,";
  print "hideHover: \047auto\047,";
  print "resize: true";
  print " });";
  print "});";

}'  static/$FILENAME
