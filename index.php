<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
require_once("pages/fidFunctions.php");
$SvrName = customURL() . str_replace('/index.php', '', $_SERVER['PHP_SELF']);
if (isset($_COOKIE['uuid'])) {
    $UUID = $_COOKIE['uuid'];
    setcookie("uuid", $_COOKIE['uuid'], time() + 3600);
} else {
    $UUID = connectSetUUID();
}
updateUUIDAlive($UUID);

$refUUID = $_COOKIE['ref'] ?? 0;
$pastebinTitle = pastebinTitle();
$pastebin = $_REQUEST['pastebin'] ?? 0;
$title = $_REQUEST['title'] ?? 0;
$expire = $_REQUEST['expire'] ?? "1";
$fidCookieCallbackURI = isset($_COOKIE['uri']) ? base64_decode($_COOKIE['uri']) : "pages/pastebinPlainEditor.html.php";
$fidCookieToken = isset($_COOKIE['token']) ? base64_decode($_COOKIE['token']) : "0";
$pastebinQR = QRUri($pastebinTLSEncryption . $SvrName . '/?ref=' . base64_encode($pastebinSenderID), '1');
$pastebinQRRawURL = QRUri($pastebinTLSEncryption . $SvrName, '0');

if (isset($_GET['ref'])) {
    if (isset($_GET['select'])) {
        $_GET['select'] == "sender" ? setcookie("ref", base64_decode($_REQUEST['ref']), time() + 7200) : 0;
        header('Location: ' . $pastebinTLSEncryption . $SvrName . '/');
    } else {
        require_once("pages/pastebinSenderSelector.html.php");
        exit;
    }
}

if (isset($_COOKIE['senderid'])) {
    $pastebinSenderURL = connectView(base64_decode($_COOKIE['senderid']));
    if ($pastebinSenderURL != "0") header('Location: ' . $pastebinTLSEncryption . $SvrName . '/' . $pastebinSenderURL);
}

if (!$pastebin || !$title) {
    $pastebinCardMessage = '';
} else {
    if (strlen($pastebin) <= PASTEBIN_MAX_LENGTH * 1024 && strlen($title) <= TITLE_MAX_LENGTH) {
        if ($fidCookieCallbackURI == "pages/pastebinPlainEditor.html.php") {
            $type = "1";
        } elseif ($fidCookieCallbackURI == "pages/pastebinMarkdownEditor.html.php") {
            $type = "2";
        } elseif ($fidCookieCallbackURI == "pages/pastebinFileUploader.html.php") {
            $type = "4";
        }
        $pastebinURL = write($pastebin, $title, $type, $expire);
        if ($refUUID) connectWrite($pastebinURL.'&ref='.$_COOKIE['senderid'], $refUUID);
        $pastebinQR = QRUri($pastebinTLSEncryption . $SvrName . '/' . $pastebinURL, '1');
        $pastebinQRRawURL = QRUri($pastebinTLSEncryption . $SvrName . '/' . $pastebinURL, '0');
        $pastebinCardMessage = '<div style="color:#26A69A">√ 创建成功 链接: <span><code><a href="' . $pastebinTLSEncryption . $SvrName . '/' . $pastebinURL . '" target="_blank"><abbr title="打开链接">' . $pastebinTLSEncryption . $SvrName . '/' . $pastebinURL . '</abbr></a></code></span></div><br>';
    } else {
        $pastebinCardMessage = '<div style="color:#e82424">× 标题过长(应少于' . TITLE_MAX_LENGTH . '字)或内容过大(应小于' . PASTEBIN_MAX_LENGTH . 'KB)[PB_TOO_BIG]</div>';
    }
}
require_once($fidCookieCallbackURI);