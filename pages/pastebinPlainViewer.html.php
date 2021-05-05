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
    <script type="application/x-javascript"> addEventListener("load", function() { setTimeout(hideURLbar, 0); }, false); function hideURLbar(){ window.scrollTo(0,1); } </script>
    <style>.center{text-align:center}</style>
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/css/mdui.min.css"
      integrity="sha384-cLRrMq39HOZdvE0j6yBojO4+1PrHfB7a9l5qLcmRm/fiWXYY+CndJPmyu5FV/9Tw"
      crossorigin="anonymous"
    />
    <title><?=$pastebinTitle?> - <?=SITE_NAME?></title>
</head>
<body class="mdui-drawer-body-left mdui-appbar-with-toolbar mdui-theme-primary-<?=$pastebinPrimaryTheme?> mdui-theme-accent-<?=$pastebinAccentTheme?> mdui-theme-layout-auto mdui-loaded">
    <header class="mdui-appbar mdui-appbar-fixed">
        <div class="mdui-toolbar mdui-color-theme">
            <span id="toggle" class="mdui-btn mdui-btn-icon mdui-ripple-white mdui-appbar-scroll-toolbar-hide "><i class="mdui-icon material-icons">menu</i></span>
            <a href="./" class="mdui-typo-headline"><?=SITE_NAME?></a>
            <button style="position: absolute; right: 50px; border-radius: 100%" class="mdui-btn mdui-btn-icon mdui-ripple mdui-ripple-purple" mdui-tooltip="{content: '二维码分享', position: 'bottom'}" mdui-dialog="{target: '#pastebin-qr'}"><i class="mdui-icon material-icons">share</i></button>
            <a href="./" style="position: absolute; right: 5px; border-radius: 100%" class="mdui-btn mdui-btn-icon mdui-ripple mdui-ripple-purple" mdui-tooltip="{content: '新建Pastebin', position: 'bottom'}"><i class="mdui-icon material-icons">add</i></a>
        </div>
        <div class="mdui-toolbar-spacer"></div>
    </header>

    <div class="mdui-drawer" id="mainDrawer">
        <div class="mdui-list" mdui-collapse="{accordion: true}" style="margin-bottom: 76px;">
            <div class="mdui-collapse-item mdui-collapse-item-open">
          <div class="mdui-collapse-item-header mdui-list-item mdui-ripple">
            <i class="mdui-list-item-icon mdui-icon material-icons mdui-text-color-red">create</i>
            <div class="mdui-list-item-content">PasteBin</div>
            <i class="mdui-collapse-item-arrow mdui-icon material-icons">keyboard_arrow_down</i>
          </div>
          <div class="mdui-collapse-item-body mdui-list">
            <a href="#" class="mdui-list-item mdui-ripple mdui-list-item-active">默认预览</a>
            <a href="./<?=base64_encode($pastebinEncodedRequest)?>&viewerType=2" class="mdui-list-item mdui-ripple ">Markdown预览</a>
          </div>
        </div>
          <div class="mdui-collapse-item-header mdui-list-item mdui-ripple">
            <i class="mdui-list-item-icon mdui-icon material-icons mdui-text-color-teal">info</i>
            <div class="mdui-list-item-content">关于</div>
            <i class="mdui-collapse-item-arrow mdui-icon material-icons">keyboard_arrow_down</i>
          </div>
          <div class="mdui-collapse-item-body mdui-list">
                        <a href="./pages/about.html" class="mdui-list-item mdui-ripple ">关于Pastebin</a>
                        <a href="./pages/manual.html" class="mdui-list-item mdui-ripple ">使用说明</a>
                                </div>
        </div>
        </div>
    </div>
    <div class="mdui-container doc-container">
        <div class="mdui-dialog" id="pastebin-qr">
            <div class="mdui-dialog-title">二维码分享</div>
            <div class="mdui-dialog-content"><div class="center"><img src="<?=$pastebinQR?>" width="300" height="300" alt=""></div></div>
            <div class="mdui-dialog-actions mdui-dialog-actions-stacked">
                <button class="mdui-btn mdui-ripple" mdui-dialog-close>取消</button>
            </div>
        </div>

        <div class="mdui-textfield mdui-textfield-floating-label mdui-textfield-not-empty">
            <div class="mdui-card mdui-hoverable" style="margin-top: 15px;border-radius:10px">
        <div class="mdui-card-primary mdui-typo">
            <?php $ref = $_REQUEST['ref'] ?? 0; if (!$ref) echo '<!--'; ?>
            <div class="mdui-chip">
                <span class="mdui-chip-icon mdui-color-amber">S</span>
                <a href="./?select=sender&ref=<?php $ref = $_REQUEST['ref'] ?? 0; echo $ref; ?>" target="_blank" class="mdui-chip-title">快速回传</a>
            </div>
            <?php $ref = $_REQUEST['ref'] ?? 0; if (!$ref) echo '-->'; ?>
            <div class="mdui-chip">
                <span class="mdui-chip-icon mdui-color-theme-accent">R</span>
                <a href="<?=$pastebinRawLink?>" target="_blank" class="mdui-chip-title">原始内容</a>
            </div>

            </div></div>
            <br>
              <label class="mdui-textfield-label">标题</label>
            <label for="title"></label><input id="title" name="title" class="mdui-textfield-input" type="text" value="<?=$pastebinTitle?>" autocomplete="off" autofocus="" required=""><br>
            <label for="pastebin"></label><textarea class="mdui-textfield-input" name="pastebin" id="pastebin" rows="25" placeholder=" Nothing to show."><?=$pastebin?></textarea>
          </div>
          <div style="text-align:center; margin: 0 auto;"><span style="color: gray;"><?=$pastebinInfo?> | <?=SITE_NAME?></span></div>
    </div>
    <button class="mdui-fab mdui-fab-fixed mdui-color-theme-accent mdui-ripple" type="submit" onclick="copyinput()"><i class="mdui-icon material-icons">content_copy</i></button>

    <script
      src="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/js/mdui.min.js"
      integrity="sha384-gCMZcshYKOGRX9r6wbDrvF+TcCCswSHFucUzUPwka+Gr+uHgjlYvkABr95TCOz3A"
      crossorigin="anonymous"
    ></script>
    <script type="text/javascript">
    	var maindrawer = new mdui.Drawer('#mainDrawer');
    	document.getElementById('toggle').addEventListener('click', function(){
    		maindrawer.toggle();
    	});
    </script>
    <SCRIPT LANGUAGE="JavaScript"> 
    function copyinput() 
    { 
    var input=document.getElementById("pastebin");
    input.select();
    document.execCommand("Copy");
    } 
    </SCRIPT>
    <script><?=$pastebinConsoleCopy?></script>
</body>
</html>