#!/bin/bash

RED='\033[1;31m'
L_GREEN='\033[1;32m'
L_BLUE='\033[1;34m'
L_GREY='\033[0;37m'
WHITE='\033[1;37m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

console() {
  local color=$1
  local msg=$2
  printf "${!color}${msg}${NC}\n"
}

error() {
  local msg=$1
  console 'RED' "==> $msg"
}

info() {
  local msg=$1
  console 'L_GREEN' "==> ${msg}"
}
warn() {
  local msg=$1
  console 'L_BLUE' "==> ${msg}"
}
