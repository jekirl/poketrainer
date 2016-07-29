<?php
/**
 * @param int $number
 * @return string
 */
function getp($number) {
  $url = $_SERVER['REQUEST_URI'];
  $url = explode('/', $url);
  if ($number == 'max') {
    for ($i = 10; $i >= 1; $i--) {
      if (isset($url[$i])) {
        return $url[$i];
      }
    }
  }
  if (isset($url[$number])) {
    return $url[$number];
  } else {
    return "";
  }
}

function getpCount() {
  $url = $_SERVER['REQUEST_URI'];
  $url = explode('/', $url);
  $count = count($url) - 2;
  return $count;
}