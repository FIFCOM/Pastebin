<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");

$SvrName = customURL() . str_replace('/index.php', '', $_SERVER['PHP_SELF']);
if (isset($_COOKIE['uuid'])) {
    $uuid = $_COOKIE['uuid'];
    setcookie("uuid", $_COOKIE['uuid'], time() + 3600);
} else {
    $uuid = setUUID();
}
updateUUIDAlive($uuid);

$refUUID = $_COOKIE['ref'] ?? 0;
$pastebinTitle = pastebinTitle();
$pastebin = $_REQUEST['pastebin'] ?? 0;
$title = $_REQUEST['title'] ?? 0;
$expire = $_REQUEST['expire'] ?? "1";
$fidCookieCallbackURI = isset($_COOKIE['uri']) ? base64_decode($_COOKIE['uri']) : "pages/pastebinPlainEditor.html.php";

if (isset($_GET['ref'])) {
    require_once("pages/pastebinConnect.html.php");
    exit();
}
require_once($fidCookieCallbackURI);