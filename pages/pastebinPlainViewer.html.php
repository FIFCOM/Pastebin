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

    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/css/mdui.min.css"
      integrity="sha384-cLRrMq39HOZdvE0j6yBojO4+1PrHfB7a9l5qLcmRm/fiWXYY+CndJPmyu5FV/9Tw"
      crossorigin="anonymous"
    />
    <title>FIFCOM Pastebin</title>
</head>
<body class="mdui-drawer-body-left mdui-appbar-with-toolbar mdui-theme-primary-<?=$pastebinPrimaryTheme?> mdui-theme-accent-<?=$pastebinAccentTheme?> mdui-theme-layout-auto mdui-loaded">
    <header class="mdui-appbar mdui-appbar-fixed">
        <div class="mdui-toolbar mdui-color-theme">
            <span id="toggle" class="mdui-btn mdui-btn-icon mdui-ripple-white mdui-appbar-scroll-toolbar-hide "><i class="mdui-icon material-icons">menu</i></span>
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
            <div class="mdui-collapse-item ">
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
    <a href="./" class="mdui-fab mdui-fab-fixed mdui-color-theme-accent" type="submit"><i class="mdui-icon material-icons">add</i></a>
    <div class="mdui-container doc-container">
        <div class="mdui-textfield mdui-textfield-floating-label mdui-textfield-not-empty">
            <div class="mdui-card" style="margin-top: 15px;border-radius:10px">
        <div class="mdui-card-primary mdui-typo">
            <?=$pastebinCardMessage?>
            </div></div>
            </br>
              <label class="mdui-textfield-label">标题</label>
              <input id="title" name="title" class="mdui-textfield-input" type="text" value="<?=$pastebinTitle?>" autocomplete="off" autofocus="" required=""></br>
                <textarea class="mdui-textfield-input" name="pastebin" id="pastebin" rows="25" placeholder=" Nothing to show."><?=$pastebin?></textarea>
                <p><input style="float: right;" class="mdui-btn mdui-color-theme-accent mdui-ripple" type="submit" value="COPY" onclick="copyinput()"></p>
          </div>
    </div>

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