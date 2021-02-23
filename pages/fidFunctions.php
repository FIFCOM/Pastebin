<?php
if( !defined('PASTEBIN_VERSION' ) ) {
    header('HTTP/1.0 403 Forbidden');
    exit();
}

function fidHideIP($ip) {
    return preg_replace('/((?:\d+\.){3})\d+/', "\\1*", $ip);
}

function fidQuery($str) {
    return "Guest";
}