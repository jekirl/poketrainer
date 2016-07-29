<?php
/**
 * @param string $url
 * @param bool $temporary
 */
function Redirect($url = null, $temporary = true) {
  defined('DOMAIN') || define('DOMAIN','');
  if (!$url) {
    $url = DOMAIN . $_SERVER['REQUEST_URI'];
  }
  if (!$temporary) {
    header("HTTP/1.1 301 Moved Permanently");
  }
  if (!headers_sent()) {
    header("Location: $url");
    exit;
  } else {
    echo "<script>window.location.href = '$url';</script>";
    exit;
  }
}