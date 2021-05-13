<?php
require_once("pages/pastebinFunctions.php");
$pastebinFileName = $_REQUEST['id'] ?? "0";
$pastebinCryptPassword = $_REQUEST['key'] ?? "0";
$pastebinRawAccessToken = $_REQUEST['token'] ?? 0;
$pastebinType = $_REQUEST['type'] ?? "txt";

if (!pastebinValidateRawAccessToken($pastebinRawAccessToken, $pastebinFileName, $pastebinCryptPassword) || !pastebinView($pastebinFileName, $pastebinCryptPassword, "info")) {
    header('HTTP/1.1 403 Forbidden');
} else {
    $pastebinDownloadFileName = pastebinView($pastebinFileName, $pastebinCryptPassword, "title") . "." .$pastebinType;
    $old = array("\\", "/", ":", "<", ">", "\"", "*", "?", "|");
    $new = array("(", ")", "-", "[", "]", "-", "~", "-", "^");
    $pastebinDownloadFileName = str_replace($old, $new, $pastebinDownloadFileName);
    $pastebinDownloadContent = pastebinView($pastebinFileName, $pastebinCryptPassword, "pastebin");
    Header ( "Content-type: application/octet-stream" );
    Header ( "Accept-Ranges: bytes" );
    Header ( "Content-Disposition: attachment; filename=" . urlencode($pastebinDownloadFileName) );
    echo $pastebinDownloadContent;
}
exit();