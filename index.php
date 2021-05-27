<?php
// 幸福往往是摸得透彻,而敬业的心却常常隐藏  ---  摸了 x9 / 10
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
require_once("pages/fidFunctions.php");
$SvrName = pastebinCustomURL() . str_replace('/index.php', '', $_SERVER['PHP_SELF']);
if (isset($_COOKIE['senderid'])) {
    $pastebinSenderID = base64_decode($_COOKIE['senderid']);
    setcookie("senderid", $_COOKIE['senderid'], time() + 7200);
} else {
    $pastebinSenderID = pastebinSenderSetID();
}
$pastebinRefID = $_COOKIE['ref'] ?? 0;
$pastebinTitle = pastebinTitle();
$pastebin = $_REQUEST['pastebin'] ?? 0;
$title = $_REQUEST['title'] ?? 0;
$expire = $_REQUEST['expire'] ?? "1";
$fidCookieCallbackURI = isset($_COOKIE['uri']) ? base64_decode($_COOKIE['uri']) : "pages/pastebinPlainEditor.html.php";
$fidCookieToken = isset($_COOKIE['token']) ? base64_decode($_COOKIE['token']) : "0";
$pastebinQR = pastebinQRUri($pastebinTLSEncryption . $SvrName . '/?ref=' . base64_encode($pastebinSenderID), '1');
$pastebinQRRawURL = pastebinQRUri($pastebinTLSEncryption . $SvrName, '0');

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
    $pastebinSenderURL = pastebinSenderView(base64_decode($_COOKIE['senderid']));
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
        $pastebinURL = pastebinWrite($pastebin, $title, $type, $expire);
        if ($pastebinRefID) pastebinSenderWrite($pastebinURL.'&ref='.$_COOKIE['senderid'], $pastebinRefID);
        $pastebinQR = pastebinQRUri($pastebinTLSEncryption . $SvrName . '/' . $pastebinURL, '1');
        $pastebinQRRawURL = pastebinQRUri($pastebinTLSEncryption . $SvrName . '/' . $pastebinURL, '0');
        $pastebinCardMessage = '<div style="color:#26A69A">√ 创建成功 链接: <span><code><a href="' . $pastebinTLSEncryption . $SvrName . '/' . $pastebinURL . '" target="_blank"><abbr title="打开链接">' . $pastebinTLSEncryption . $SvrName . '/' . $pastebinURL . '</abbr></a></code></span></div><br>';
    } else {
        $pastebinCardMessage = '<div style="color:#e82424">× 标题过长(应少于' . TITLE_MAX_LENGTH . '字)或内容过大(应小于' . PASTEBIN_MAX_LENGTH . 'KB)[PB_TOO_BIG]</div>';
    }
}
require_once($fidCookieCallbackURI);