<?php
if( !defined('PASTEBIN_VERSION' ) ) {
    header('HTTP/1.0 403 Forbidden');
    exit();
}

function fidHideIP($ip) {
    return preg_replace('/((?:\d+\.){2})\d+/', "\\1*", $ip);
}

function fidQuery($str): string
{
    return "Guest";
}

function fidIsset($token): int
{
    if (isset($token)){
        if ($token == "0") return 0; else return 1;
    } else {
        return 0;
    }
}