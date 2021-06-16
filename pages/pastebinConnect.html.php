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
                <div id="msg"><div class="mdui-progress"><div class="mdui-progress-indeterminate"></div></div><div class="center mdui-typo"><br><strong>正在连接...</strong><br></div>
                </div>
            </div>

        </div>

        <div class="mdui-card" style="margin-top: 15px;border-radius:10px">
            <div class="mdui-card-primary mdui-typo">
                <a href="./" class="mdui-btn mdui-btn-raised mdui-ripple mdui-color-theme-accent mdui-btn-block"><strong>返回主页</strong></a>
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
        let reg = new RegExp("(^|&)" + 'ref' + "=([^&]*)(&|$)", "i")
        let r = window.location.search.substr(1).match(reg)
        let target
        if (r != null) target =  unescape(r[2])
        console.log(target)
        if (getCookie("uuid") === target) {
            window.location.href = '<?=$scheme?><?=$SvrName?>'
        } else {
            let data = {}
            data['target'] = target
            $.ajax({
                method: 'POST',
                url: '<?=$scheme?><?=$SvrName?>/api.php?action=connectNew&uuid=' + getCookie("uuid"),
                data: data,
                complete: function (data) {
                    let json = JSON.parse(data.responseText);
                    console.log(json['code'])
                    if (json['code'] === 0) {
                        document.getElementById('msg').innerHTML = '<div class="mdui-progress"><div class="mdui-progress-indeterminate"></div></div><div class="center mdui-typo"><br><strong>对方可能不在线,重连中...</strong><br></div>'
                    }
                }
            })
            window.setInterval(pastebinConnectNew, 2000);
        }
    }

    function pastebinConnectNew() {
        let reg = new RegExp("(^|&)" + 'ref' + "=([^&]*)(&|$)", "i")
        let r = window.location.search.substr(1).match(reg)
        let target
        if (r != null) target =  unescape(r[2])
        let data = {}
        data['target'] = target
        console.log(target)
        $.ajax({
            method: 'POST',
            url: '<?=$scheme?><?=$SvrName?>/api.php?action=connectNew&uuid=' + getCookie("uuid"),
            data: data,
            complete: function (data) {
                //console.log(data.responseText)
                let json = JSON.parse(data.responseText);
                console.log(json['code'])
                if (json['code'] === 2) {
                    // connected , write cookie and redirect
                    setCookie("connect_target_uuid", target, 3600)
                    window.location.href = '<?=$scheme?><?=$SvrName?>'
                } else if (json['code'] === 1) {
                    // waiting
                    document.getElementById('msg').innerHTML = '<div class="mdui-progress"><div class="mdui-progress-indeterminate"></div></div><div class="center mdui-typo"><br><strong>正在连接...</strong><br></div>'
                } else if (json['code'] === 0) {
                    // connect error , end
                    document.getElementById('msg').innerHTML = '<div class="mdui-progress"><div class="mdui-progress-indeterminate"></div></div><div class="center mdui-typo"><br><strong>对方可能不在线,重连中...</strong><br></div>'
                }
            }
        })
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