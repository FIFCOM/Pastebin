<?php
header("Content-type:text/html;charset=utf-8;");
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
require_once("pages/fidFunctions.php");
$SvrName = pastebinCustomURL() . str_replace('/index.php', '', $_SERVER['PHP_SELF']);
$pastebinTitle = pastebinTitle();
$pastebin = isset($_REQUEST['pastebin']) ? $_REQUEST['pastebin'] : 0;
$title = isset($_REQUEST['title']) ? $_REQUEST['title'] : 0;
$fidCookieCallbackURI = isset($_COOKIE['uri']) ? base64_decode($_COOKIE['uri']) : "pages/pastebinPlainEditor.html.php";
$fidCookieToken = isset($_COOKIE['token']) ? base64_decode($_COOKIE['token']) : "0";
$pastebinQR = pastebinQRUri($pastebinTLSEncryption . $SvrName, '1');
$pastebinQRRawURL = pastebinQRUri($pastebinTLSEncryption . $SvrName, '0');
if (!$pastebin || !$title) {
    $pastebinCardMessage = '
                <label class="mdui-radio"><input type="radio" name="expire" value="7"/><i class="mdui-radio-icon"></i>一周有效</label>
                <label class="mdui-radio"><input type="radio" name="expire" value="31" checked/><i class="mdui-radio-icon"></i>一个月有效</label>
                <label class="mdui-radio"><input type="radio" name="expire" value="366"/><i class="mdui-radio-icon"></i>一年有效</label>
                <label class="mdui-radio"><input type="radio" name="expire" value="0"/><i class="mdui-radio-icon"></i>永久有效</label>';
} else {
    if (strlen($pastebin) <= PASTEBIN_MAX_LENTH && strlen($title) <= TITLE_MAX_LENTH) {
        if ($fidCookieCallbackURI == "pages/pastebinPlainEditor.html.php") {
            $type = "1";
        } elseif ($fidCookieCallbackURI == "pages/pastebinMarkdownEditor.html.php") {
            $type = "2";
        }
        $pastebinURL = pastebinWrite($pastebin, $title, $type);
        $pastebinQR = pastebinQRUri($pastebinTLSEncryption . $SvrName . '/' . $pastebinURL, '1');
        $pastebinQRRawURL = pastebinQRUri($pastebinTLSEncryption . $SvrName . '/' . $pastebinURL, '0');
        $pastebinCardMessage = '<div style="color:#26A69A">创建成功√  链接: <span><code><a href="' . $pastebinTLSEncryption . $SvrName . '/' . $pastebinURL . '" target="_blank"><abbr title="打开链接">' . $pastebinTLSEncryption . $SvrName . '/' . $pastebinURL . '</abbr></a></code></span></div>  ';
    } else {
        $pastebinCardMessage = '标题过长(不超过100字)或内容过大(不大于100KB)[PB_ERR_TOO_BIG]';
    }
}
require_once($fidCookieCallbackURI);
?>