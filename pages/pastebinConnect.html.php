<?php
if (!defined('PASTEBIN_VERSION')) {
    header('HTTP/1.0 403 Forbidden');
    exit();
}
ini_set('display_errors', 0);
?>
<!doctype html>
<html lang="zh-cmn-Hans">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <meta name="keywords" content="PasteBin service developed by FIFCOM"/>
    <link rel="shortcut icon" href="<?= $pastebinIcon ?>"/>
    <style>.center {
            text-align: center
        }</style>
    <script type="application/x-javascript"> addEventListener("load", function () {
            setTimeout(hideURLbar, 0);
        }, false);

        function hideURLbar() {
            window.scrollTo(0, 1);
        } </script>
    <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/css/mdui.min.css"
        integrity="sha384-cLRrMq39HOZdvE0j6yBojO4+1PrHfB7a9l5qLcmRm/fiWXYY+CndJPmyu5FV/9Tw"
        crossorigin="anonymous"
    />
    <title><?= SITE_NAME ?></title>
</head>
<body class="mdui-appbar-with-toolbar mdui-theme-primary-<?= $pastebinPrimaryTheme ?> mdui-theme-accent-<?= $pastebinAccentTheme ?> mdui-theme-layout-auto mdui-loaded">
<header class="mdui-appbar mdui-appbar-fixed">
    <div class="mdui-toolbar mdui-color-theme">
        <a href="./" class="mdui-typo-headline"><?= SITE_NAME ?></a>
    </div>
</header>

<div class="mdui-container doc-container">


    <div class="mdui-textfield mdui-textfield-floating-label mdui-textfield-not-empty">
        <div class="mdui-card" style="margin-top: 15px;border-radius:10px">
            <div class="mdui-card-primary mdui-typo">
                <div class="mdui-typo" id="msg"></div>
            </div>
        </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/js/mdui.min.js"
        integrity="sha384-gCMZcshYKOGRX9r6wbDrvF+TcCCswSHFucUzUPwka+Gr+uHgjlYvkABr95TCOz3A"
        crossorigin="anonymous"
></script>
<script>
    let $ = mdui.$;

    window.onload = function () {
        if (document.cookie.indexOf("connect_target_uuid=") !== -1) {
            document.getElementById('connect_card').innerHTML = '<div class="mdui-card" style="margin-top: 15px;border-radius:10px">'
                + '<div class="mdui-card-primary mdui-typo"><label class="mdui-checkbox">'
                + '<input type="checkbox" name="target" value="'
                + getCookie('connect_target_uuid') + '"/><i class="mdui-checkbox-icon"></i>'
                + '发送给' + getCookie('connect_target_uuid').substr(0,6)  + '</label></div></div><br>'
        }
        window.setInterval(pastebinConnectNew, 2000);
    }



    function getCookie(name) {
        let prefix = name + "="
        let start = document.cookie.indexOf(prefix)
        if (start === -1) {
            return null;
        }
        let end = document.cookie.indexOf(";", start + prefix.length)
        if (end === -1) {
            end = document.cookie.length;
        }
        let value = document.cookie.substring(start + prefix.length, end)
        return unescape(value);
    }
    function setCookie(name, val, time) {
        let d = new Date();
        d.setTime(d.getTime() + time*1000);
        let expires = "expires="+d.toUTCString();
        document.cookie = name + "=" + val + "; " + expires;
    }
</script>
<script><?= $consoleCopyright ?></script>
</body>
</html>