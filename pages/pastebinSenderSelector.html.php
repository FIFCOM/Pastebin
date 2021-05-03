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
    <meta name="keywords" content="Pastebin service developed by FIFCOM"/>
    <link rel="shortcut icon" href="<?= $pastebinIcon ?>"/>
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
        <a href="./" style="position: absolute; right: 5px; border-radius: 100%"
           class="mdui-btn mdui-btn-icon mdui-ripple mdui-ripple-purple"
           mdui-tooltip="{content: '新建Pastebin', position: 'bottom'}"><i class="mdui-icon material-icons">add</i></a>
    </div>
    <div class="mdui-toolbar-spacer"></div>
</header>
<div class="mdui-container doc-container">
    <div class="mdui-textfield mdui-textfield-floating-label mdui-textfield-not-empty">
        <div class="mdui-card" style="margin-top: 15px;border-radius:10px">
            <div class="mdui-card-primary mdui-typo">
                <b>Pastebin Sender : 请选择模式</b>
                <br><br><br>
                <a href="./?ref=<?= $_GET['ref'] ?>&select=sender"
                   class="mdui-btn mdui-btn-block mdui-color-theme-accent mdui-ripple">向您所扫描二维码的设备发送一次Pastebin</a>
                <br><br><br>
                <a href="./?ref=<?= $_GET['ref'] ?>&select=plain"
                   class="mdui-btn mdui-btn-block mdui-color-theme-accent mdui-ripple">创建默认的Pastebin</a>
            </div>
        </div>

    </div>
    <div style="text-align:center; margin: 0 auto;"><span style="color: gray;"><?= SITE_NAME ?></span></div>
</div>

<script
        src="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/js/mdui.min.js"
        integrity="sha384-gCMZcshYKOGRX9r6wbDrvF+TcCCswSHFucUzUPwka+Gr+uHgjlYvkABr95TCOz3A"
        crossorigin="anonymous"
></script>
<script><?= $pastebinConsoleCopy ?></script>
</body>
</html>