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
<body class="mdui-drawer-body-left mdui-appbar-with-toolbar mdui-theme-primary-<?= $pastebinPrimaryTheme ?> mdui-theme-accent-<?= $pastebinAccentTheme ?> mdui-theme-layout-auto mdui-loaded">
<header class="mdui-appbar mdui-appbar-fixed">
    <div class="mdui-toolbar mdui-color-theme">
        <span id="toggle" class="mdui-btn mdui-btn-icon mdui-ripple-white mdui-appbar-scroll-toolbar-hide "><i
                    class="mdui-icon material-icons">menu</i></span>
        <a href="./" class="mdui-typo-headline"><?= SITE_NAME ?></a>
        <button style="position: absolute; right: 50px; border-radius: 100%"
                class="mdui-btn mdui-btn-icon mdui-ripple mdui-ripple-purple"
                mdui-tooltip="{content: '二维码分享', position: 'bottom'}" mdui-dialog="{target: '#pastebin-qr'}"><i
                    class="mdui-icon material-icons">share</i></button>
        <a href="./" target="_blank" style="position: absolute; right: 5px; border-radius: 100%"
           class="mdui-btn mdui-btn-icon mdui-ripple mdui-ripple-purple"
           mdui-tooltip="{content: '新建Pastebin', position: 'bottom'}"><i class="mdui-icon material-icons">add</i></a>
    </div>
    <div class="mdui-toolbar-spacer"></div>
</header>

<div class="mdui-drawer" id="mainDrawer">
    <div class="mdui-list" mdui-collapse="{accordion: true}" style="margin-bottom: 76px;">
        <div class="mdui-collapse-item mdui-collapse-item-open">
            <div class="mdui-collapse-item-header mdui-list-item mdui-ripple">
                <i class="mdui-list-item-icon mdui-icon material-icons mdui-text-color-red">create</i>
                <div class="mdui-list-item-content">Pastebin</div>
                <i class="mdui-collapse-item-arrow mdui-icon material-icons">keyboard_arrow_down</i>
            </div>
            <div class="mdui-collapse-item-body mdui-list">
                <a href="./" class="mdui-list-item mdui-ripple mdui-list-item-active">默认编辑器</a>
                <a href="./fid.php?action=cookie&uri=cGFnZXMvcGFzdGViaW5NYXJrZG93bkVkaXRvci5odG1sLnBocA=="
                   class="mdui-list-item mdui-ripple ">Markdown编辑器</a>
            </div>
        </div>
        <div class="mdui-collapse-item">
            <div class="mdui-collapse-item-header mdui-list-item mdui-ripple">
                <i class="mdui-list-item-icon mdui-icon material-icons mdui-text-color-deep-orange">account_circle</i>
                <div class="mdui-list-item-content">我的</div>
                <i class="mdui-collapse-item-arrow mdui-icon material-icons">keyboard_arrow_down</i>
            </div>
            <div class="mdui-collapse-item-body mdui-list">
                <a href="./fid.php?action=redirect&uri=pages/my-pb.php"
                   class="mdui-list-item mdui-ripple ">我的Pastebin</a>
                <a href="./fid.php?action=redirect&uri=pages/share.php" class="mdui-list-item mdui-ripple ">我的分享</a>
                <a href="./fid.php?action=accountInfo" class="mdui-list-item mdui-ripple ">账号管理</a>
            </div>
        </div>
        <div class="mdui-collapse-item">
            <div class="mdui-collapse-item-header mdui-list-item mdui-ripple">
                <i class="mdui-list-item-icon mdui-icon material-icons mdui-text-color-blue">code</i>
                <div class="mdui-list-item-content">API</div>
                <i class="mdui-collapse-item-arrow mdui-icon material-icons">keyboard_arrow_down</i>
            </div>
            <div class="mdui-collapse-item-body mdui-list">
                <a href="./fid.php?action=redirect&uri=api/my-api.php" class="mdui-list-item mdui-ripple ">My API</a>
                <a href="./api/api-docs.php" class="mdui-list-item mdui-ripple ">API文档</a>
            </div>
        </div>
        <div class="mdui-collapse-item ">
            <div class="mdui-collapse-item-header mdui-list-item mdui-ripple">
                <i class="mdui-list-item-icon mdui-icon material-icons mdui-text-color-teal">info</i>
                <div class="mdui-list-item-content">关于</div>
                <i class="mdui-collapse-item-arrow mdui-icon material-icons">keyboard_arrow_down</i>
            </div>
            <div class="mdui-collapse-item-body mdui-list">
                <a href="./pages/about.html" class="mdui-list-item mdui-ripple ">关于Pastebin</a>
                <a href="./fid.php?action=redirect&uri=pages/privacy.php" class="mdui-list-item mdui-ripple ">隐私政策</a>
                <a href="./pages/manual.html" class="mdui-list-item mdui-ripple ">使用说明</a>
            </div>
        </div>
    </div>
</div>

<div class="mdui-container doc-container">
    <div class="mdui-dialog" id="pastebin-qr">
        <div class="mdui-dialog-title">二维码分享</div>
        <div class="mdui-dialog-content">
            <div class="center"><img src="<?= $pastebinQR ?>" width="300" height="300" alt="">
                <?php if ($pastebinURL) echo '<!--'; ?>
                <div class="mdui-typo-body-2-opacity">扫描二维码可向此页面快速分享Pastebin，对方创建后请刷新此页面</div>
                <?php if ($pastebinURL) echo '-->'; ?>
            </div>
        </div>
        <div class="mdui-dialog-actions">
            <?php if ($pastebinURL) echo '<!--'; ?>
            <a href="./" class="mdui-btn mdui-ripple">刷新</a>
            <?php if ($pastebinURL) echo '-->'; ?>
            <button class="mdui-btn mdui-ripple" mdui-dialog-close>取消</button>
        </div>
    </div>

    <div class="mdui-textfield mdui-textfield-floating-label mdui-textfield-not-empty">
        <div class="mdui-card" style="margin-top: 15px;border-radius:10px">
            <form action="#" method="post">
                <div class="mdui-card-primary mdui-typo">
                    <?= $pastebinCardMessage ?>
                    <label class="mdui-radio"><input type="radio" name="expire" value="8"/><i
                                class="mdui-radio-icon"></i>一周有效</label>
                    <label class="mdui-radio"><input type="radio" name="expire" value="31" checked/><i
                                class="mdui-radio-icon"></i>一个月有效</label>
                    <label class="mdui-radio"><input type="radio" name="expire" value="181"/><i
                                class="mdui-radio-icon"></i>半年有效</label>
                    <label class="mdui-radio"><input type="radio" name="expire" value="366"/><i
                                class="mdui-radio-icon"></i>一年有效</label>
                </div>
        </div>
        <br>
        <label class="mdui-textfield-label">标题</label>
        <label for="title"></label><input id="title" name="title" class="mdui-textfield-input" type="text"
                                          value="<?= $pastebinTitle ?>"
                                          autocomplete="off" autofocus="" required=""><br>
        <label for="pastebin"></label><textarea class="mdui-textfield-input" name="pastebin" id="pastebin" rows="24"
                                                placeholder=" Enter text..."></textarea>
    </div>
</div>
<button class="mdui-fab mdui-fab-fixed mdui-color-theme-accent mdui-ripple" type="submit"><i
            class="mdui-icon material-icons">add</i></button>
</form>
<script
        src="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/js/mdui.min.js"
        integrity="sha384-gCMZcshYKOGRX9r6wbDrvF+TcCCswSHFucUzUPwka+Gr+uHgjlYvkABr95TCOz3A"
        crossorigin="anonymous"
></script>
<script type="text/javascript">
    var maindrawer = new mdui.Drawer('#mainDrawer');
    document.getElementById('toggle').addEventListener('click', function () {
        maindrawer.toggle();
    });
</script>
<script><?= $pastebinConsoleCopy ?></script>
</body>
</html>