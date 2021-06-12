<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
$pastebinEncodedRequest = (isset($_REQUEST['pb']) && strlen(base64_decode($_REQUEST['pb'])) >= 19 && strlen(base64_decode($_REQUEST['pb'])) <= 21) ? base64_decode($_REQUEST['pb']) : "0";
if ($pastebinEncodedRequest) {
    $pastebinFileName = getSubString($pastebinEncodedRequest, "$", "+");
    $pastebinCryptPassword = dechex(crc32(getSubString($pastebinEncodedRequest, "+", "-")));
    $pastebinViewerType = $_REQUEST['viewerType'] ?? getSubString($pastebinEncodedRequest, "-", "!");
    $pastebinRawAccessToken = md5(date("y") . date("m") . date("d") . $pastebinFileName . $pastebinCryptPassword . $_SERVER['REMOTE_ADDR'] . PASTEBIN_SECURITY_TOKEN);
} else {
    header('HTTP/1.0 403 Forbidden');
    exit();
}
$SvrName = customURL() . str_replace('/view.php', '', $_SERVER['PHP_SELF']);
$pastebinInfo = view($pastebinFileName, $pastebinCryptPassword, "info");
$pastebinPlainViewerLink = "" . $scheme . $SvrName . '/' . base64_encode($pastebinEncodedRequest) . '&viewerType=1';
$pastebinDownloadLink = "" . $scheme . $SvrName . '/download.php?id=' . $pastebinFileName . '&key=' . $pastebinCryptPassword . '&token=' . $pastebinRawAccessToken;
$pastebinTitle = view($pastebinFileName, $pastebinCryptPassword, "title");
$pastebin = view($pastebinFileName, $pastebinCryptPassword, "pastebin");
$pastebinQR = QRUri($scheme . $SvrName . '/' . base64_encode($pastebinEncodedRequest), '1');
$pastebinQRRawURL = QRUri($scheme . $SvrName . '/' . base64_encode($pastebinEncodedRequest), '0');
if ($pastebinViewerType == "1") {
    require_once("pages/pastebinPlainViewer.html.php");
    exit();
} elseif ($pastebinViewerType == "2") {
    require_once("pages/pastebinMarkdownViewer.html.php");
    exit();
} else {
    header('HTTP/1.0 403 Forbidden');
    exit();
}
