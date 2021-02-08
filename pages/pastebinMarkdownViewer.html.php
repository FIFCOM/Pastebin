<?php
if( !defined('PASTEBIN_VERSION' ) ) {
    header('HTTP/1.0 403 Forbidden');
    exit();
}
ini_set('display_errors', 0);
?>
<!doctype html>
<html lang="zh-cmn-Hans">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="keywords" content="PasteBin service developed by FIFCOM" />
    <link rel="shortcut icon" href="<?=$pastebinIcon?>"/>
    <link rel="stylesheet" href="pages/md/css/editormd.preview.css" />
    <link rel="stylesheet" href="pages/md/css/editormd.min.css" />
    <script type="application/x-javascript"> addEventListener("load", function() { setTimeout(hideURLbar, 0); }, false); function hideURLbar(){ window.scrollTo(0,1); } </script>
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/css/mdui.min.css"
      integrity="sha384-cLRrMq39HOZdvE0j6yBojO4+1PrHfB7a9l5qLcmRm/fiWXYY+CndJPmyu5FV/9Tw"
      crossorigin="anonymous"
    />
    <title>FIFCOM Pastebin</title>
</head>
<body class="mdui-appbar-with-toolbar mdui-theme-primary-<?=$pastebinPrimaryTheme?> mdui-theme-accent-<?=$pastebinAccentTheme?> mdui-theme-layout-auto mdui-loaded">
    <header class="mdui-appbar mdui-appbar-fixed">
        <div class="mdui-toolbar mdui-color-theme">
            <a href="../" class="mdui-typo-headline">FIFCOM Pastebin</a>
            <a href="https://github.com/FIFCOM/Pastebin" target="_blank" style="position: absolute; right: 5px; border-radius: 100%" class="mdui-btn mdui-btn-icon mdui-ripple mdui-ripple-purple" mdui-tooltip="{content: '源代码-Github', position: 'bottom'}">
            <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 36 36" enable-background="new 0 0 36 36" xml:space="preserve" class="mdui-icon" style="width: 24px;height:24px;">
                <path fill-rule="evenodd" clip-rule="evenodd" fill="#FFFFFF" d="M18,1.4C9,1.4,1.7,8.7,1.7,17.7c0,7.2,4.7,13.3,11.1,15.5
                c0.8,0.1,1.1-0.4,1.1-0.8c0-0.4,0-1.4,0-2.8c-4.5,1-5.5-2.2-5.5-2.2c-0.7-1.9-1.8-2.4-1.8-2.4c-1.5-1,0.1-1,0.1-1
                c1.6,0.1,2.5,1.7,2.5,1.7c1.5,2.5,3.8,1.8,4.7,1.4c0.1-1.1,0.6-1.8,1-2.2c-3.6-0.4-7.4-1.8-7.4-8.1c0-1.8,0.6-3.2,1.7-4.4
                c-0.2-0.4-0.7-2.1,0.2-4.3c0,0,1.4-0.4,4.5,1.7c1.3-0.4,2.7-0.5,4.1-0.5c1.4,0,2.8,0.2,4.1,0.5c3.1-2.1,4.5-1.7,4.5-1.7
                c0.9,2.2,0.3,3.9,0.2,4.3c1,1.1,1.7,2.6,1.7,4.4c0,6.3-3.8,7.6-7.4,8c0.6,0.5,1.1,1.5,1.1,3c0,2.2,0,3.9,0,4.5
                c0,0.4,0.3,0.9,1.1,0.8c6.5-2.2,11.1-8.3,11.1-15.5C34.3,8.7,27,1.4,18,1.4z"></path>
            </svg></a>
        </div>
        <div class="mdui-toolbar-spacer"></div>
    </header>
    <a href="./" class="mdui-fab mdui-fab-fixed mdui-color-theme-accent" type="submit"><i class="mdui-icon material-icons">add</i></a>
    <div class="mdui-container doc-container">
        <div class="mdui-textfield mdui-textfield-floating-label mdui-textfield-not-empty">
            <div class="mdui-card" style="margin-top: 15px;border-radius:10px">
        <div class="mdui-card-primary mdui-typo">
            <?=$pastebinMarkdownCardMessage?>
            </div></div>
            </br>
              <label class="mdui-textfield-label">标题</label>
              <input id="title" name="title" class="mdui-textfield-input" type="text" value="<?=$pastebinTitle?>" autocomplete="off" autofocus="" required=""></br>
                <div id="pastebin-editormd"><textarea name="pastebin" id="pastebin" style="display:none;"><?=$pastebin?></textarea></div>
                <!-- <p><input style="float: right;" class="mdui-btn mdui-color-theme-accent mdui-ripple" type="submit" value="COPY" onclick="copyinput()"></p> -->
          </div>
    </div>

    <script
      src="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/js/mdui.min.js"
      integrity="sha384-gCMZcshYKOGRX9r6wbDrvF+TcCCswSHFucUzUPwka+Gr+uHgjlYvkABr95TCOz3A"
      crossorigin="anonymous"
    ></script>
    <script src="https://cdn.bootcss.com/jquery/3.4.1/jquery.min.js"></script>
    <script src="pages/md/editormd.js"></script>
    <script src="pages/md/lib/marked.min.js"></script>
    <script src="pages/md/lib/prettify.min.js"></script>  
    <script src="pages/md/lib/raphael.min.js"></script>
    <script src="pages/md/lib/underscore.min.js"></script>
    <script src="pages/md/lib/sequence-diagram.min.js"></script>
    <script src="pages/md/lib/flowchart.min.js"></script>
    <script src="pages/md/lib/jquery.flowchart.min.js"></script>
    <script type="text/javascript">
        $(function() {
            pastebinEditormdViewer = editormd.markdownToHTML("pastebin-editormd", {
                    htmlDecode      : true, //htmlDecode      : "style,script,iframe",
                    tocm            : true,
                    emoji           : true,
                    taskList        : true,
                    tex             : true,
                    flowChart       : true,
                    sequenceDiagram : true,
                });
            });
    </script>
    <script><?=$pastebinConsoleCopy?></script>
</body>
</html>