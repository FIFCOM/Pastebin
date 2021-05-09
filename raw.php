<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
require_once("pages/fidFunctions.php");
$pastebinFileName = $_REQUEST['id'] ?? "0";
$pastebinCryptPassword = $_REQUEST['key'] ?? "0";
$pastebinRawAccessToken = $_REQUEST['token'] ?? "00000000000000000000000000000000";
$pastebinType = $_REQUEST['type'] ?? "pastebin";
$pastebinHeaderReferer = $_SERVER["HTTP_REFERER"] ?? 0;

if ($pastebinHeaderReferer && pastebinValidateRawAccessToken($pastebinRawAccessToken, $pastebinFileName, $pastebinCryptPassword) == 0) {
    header('HTTP/1.0 403 Forbidden');
    exit();
}

if ($pastebinFileName && $pastebinCryptPassword ) {
    $pastebinRaw = pastebinView($pastebinFileName, $pastebinCryptPassword, $pastebinType);
    header("Content-type:text/plain;charset=utf-8;");
    echo $pastebinRaw;
} else {
    header('HTTP/1.0 403 Forbidden');
    exit();
}