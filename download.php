<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");

$pastebinFileName = $_REQUEST['id'] ?? "0";
$pastebinCryptPassword = $_REQUEST['key'] ?? "0";
$pastebinRawAccessToken = $_REQUEST['token'] ?? 0;
$pastebinType = $_REQUEST['type'] ?? "txt";

if (!validateRawAccessToken($pastebinRawAccessToken, $pastebinFileName, $pastebinCryptPassword) || !view($pastebinFileName, $pastebinCryptPassword, "info")) {
    header('HTTP/1.1 403 Forbidden');
} else {
    $pastebinDownloadFileName = view($pastebinFileName, $pastebinCryptPassword, "title") . "." .$pastebinType;
    $old = array("\\", "/", ":", "<", ">", "\"", "*", "?", "|");
    $new = array("(", ")", "-", "[", "]", "-", "~", "-", "^");
    $pastebinDownloadFileName = str_replace($old, $new, $pastebinDownloadFileName);
    $pastebinDownloadContent = view($pastebinFileName, $pastebinCryptPassword, "pastebin");
    Header ( "Content-type: application/octet-stream" );
    Header ( "Accept-Ranges: bytes" );
    Header ( "Content-Disposition: attachment; filename=" . urlencode($pastebinDownloadFileName) );
    echo $pastebinDownloadContent;
}
exit();