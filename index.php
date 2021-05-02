<?php
header("Content-type:text/html;charset=utf-8;");
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
require_once("pages/fidFunctions.php");
$SvrName = pastebinCustomURL() . str_replace('/index.php', '', $_SERVER['PHP_SELF']);
$pastebinTitle = pastebinTitle();
$pastebin = $_REQUEST['pastebin'] ?? 0;
$title = $_REQUEST['title'] ?? 0;
$expire = $_REQUEST['expire'] ?? "8";
$fidCookieCallbackURI = isset($_COOKIE['uri']) ? base64_decode($_COOKIE['uri']) : "pages/pastebinPlainEditor.html.php";
$fidCookieToken = isset($_COOKIE['token']) ? base64_decode($_COOKIE['token']) : "0";
$pastebinQR = pastebinQRUri($pastebinTLSEncryption . $SvrName, '1');
$pastebinQRRawURL = pastebinQRUri($pastebinTLSEncryption . $SvrName, '0');
if (!$pastebin || !$title) {
    $pastebinCardMessage = '
                <label class="mdui-radio"><input type="radio" name="expire" value="8"/><i class="mdui-radio-icon"></i>一周有效</label>
                <label class="mdui-radio"><input type="radio" name="expire" value="31" checked/><i class="mdui-radio-icon"></i>一个月有效</label>
                <label class="mdui-radio"><input type="radio" name="expire" value="181"/><i class="mdui-radio-icon"></i>半年有效</label>
                <label class="mdui-radio"><input type="radio" name="expire" value="366"/><i class="mdui-radio-icon"></i>一年有效</label>';
} else {
    if (strlen($pastebin) <= PASTEBIN_MAX_LENGTH && strlen($title) <= TITLE_MAX_LENGTH) {
        if ($fidCookieCallbackURI == "pages/pastebinPlainEditor.html.php") {
            $type = "1";
        } elseif ($fidCookieCallbackURI == "pages/pastebinMarkdownEditor.html.php") {
            $type = "2";
        } elseif ($fidCookieCallbackURI == "pages/pastebinFileUploader.html.php") {
            $type = "4";
        }
        $pastebinURL = pastebinWrite($pastebin, $title, $type, $expire);
        $pastebinQR = pastebinQRUri($pastebinTLSEncryption . $SvrName . '/' . $pastebinURL, '1');
        $pastebinQRRawURL = pastebinQRUri($pastebinTLSEncryption . $SvrName . '/' . $pastebinURL, '0');
        $pastebinCardMessage = '<div style="color:#26A69A">创建成功√  链接: <span><code><a href="' . $pastebinTLSEncryption . $SvrName . '/' . $pastebinURL . '" target="_blank"><abbr title="打开链接">' . $pastebinTLSEncryption . $SvrName . '/' . $pastebinURL . '</abbr></a></code></span></div>  ';
    } else {
        $pastebinCardMessage = '<div style="color:#e82424">× 标题过长(不超过'.TITLE_MAX_LENGTH.'字)或内容过大(不大于'.PASTEBIN_MAX_LENGTH .'KB)[PB_TOO_BIG]</div>';
    }
}
require_once($fidCookieCallbackURI);