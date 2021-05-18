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
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/css/editormd.preview.css"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/css/editormd.min.css"/>
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
    <title><?= $pastebinTitle ?> - <?= SITE_NAME ?></title>
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
                <?php $ref = $_REQUEST['ref'] ?? 0; if (!$ref) echo '<!--'; ?>
                <div class="mdui-chip mdui-hoverable">
                    <span class="mdui-chip-icon mdui-color-amber">S</span>
                    <a href="./?select=sender&ref=<?php $ref = $_REQUEST['ref'] ?? 0; echo $ref; ?>" target="_blank" class="mdui-chip-title">快速回传</a>
                </div>
                <?php $ref = $_REQUEST['ref'] ?? 0; if (!$ref) echo '-->'; ?>
                <div class="mdui-chip mdui-hoverable">
                    <span class="mdui-chip-icon mdui-color-teal">D</span>
                    <a href="<?=$pastebinDownloadLink?>&type=md" class="mdui-chip-title">下载</a>
                </div>
                <div class="mdui-chip mdui-hoverable">
                    <span class="mdui-chip-icon mdui-color-theme-accent">P</span>
                    <a href="<?=$pastebinPlainViewerLink?>" class="mdui-chip-title">查看源代码</a>
                </div>
            </div>
        </div>
        <br>
        <label class="mdui-textfield-label">标题</label>
        <label for="title"></label><input id="title" name="title" class="mdui-textfield-input" type="text"
                                          value="<?= $pastebinTitle ?>" autocomplete="off" autofocus="" required=""><br>
        <div id="pastebin-editormd"><label for="pastebin"></label><textarea name="pastebin" id="pastebin"
                                                                            style="display:none;"><?= $pastebin ?></textarea>
        </div>
    </div>
    <div style="text-align:center; margin: 0 auto;"><span
                style="color: gray;"><?= $pastebinInfo ?> | <?= SITE_NAME ?></span></div>
</div>

<script
        src="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/js/mdui.min.js"
        integrity="sha384-gCMZcshYKOGRX9r6wbDrvF+TcCCswSHFucUzUPwka+Gr+uHgjlYvkABr95TCOz3A"
        crossorigin="anonymous"
></script>
<script src="https://cdn.bootcss.com/jquery/3.4.1/jquery.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/editormd.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/prettify.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/raphael.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/underscore.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/sequence-diagram.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/flowchart.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/jquery.flowchart.min.js"></script>
<script type="text/javascript">
    $(function () {
        const pastebinEditormdViewer = editormd.markdownToHTML("pastebin-editormd", {
            htmlDecode: "script,iframe", //htmlDecode      : "style,script,iframe" / true / false, <--- example
            tocm: true,
            emoji: true,
            taskList: true,
            tex: true,
            flowChart: true,
            sequenceDiagram: true,
        });
    });
</script>
<script><?= $pastebinConsoleCopy ?></script>
</body>
</html>