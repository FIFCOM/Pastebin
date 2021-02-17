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
    <meta name="keywords" content="FIFCOM PasteBin" />
    <link rel="shortcut icon" href="<?=$pastebinIcon?>"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/css/editormd.preview.min.css" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/css/editormd.min.css" />
    <style>.center{text-align:center}</style>
    <script type="application/x-javascript"> addEventListener("load", function() { setTimeout(hideURLbar, 0); }, false); function hideURLbar(){ window.scrollTo(0,1); } </script>
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/mdui@1.0.1/dist/css/mdui.min.css"
      integrity="sha384-cLRrMq39HOZdvE0j6yBojO4+1PrHfB7a9l5qLcmRm/fiWXYY+CndJPmyu5FV/9Tw"
      crossorigin="anonymous"
    />
    <title><?=SITE_NAME?></title>
</head>
<body class="mdui-drawer-body-left mdui-appbar-with-toolbar mdui-theme-primary-<?=$pastebinPrimaryTheme?> mdui-theme-accent-<?=$pastebinAccentTheme?> mdui-theme-layout-auto mdui-loaded">
    <header class="mdui-appbar mdui-appbar-fixed">
    <div class="mdui-toolbar mdui-color-theme">
            <span id="toggle" class="mdui-btn mdui-btn-icon mdui-ripple-white mdui-appbar-scroll-toolbar-hide "><i class="mdui-icon material-icons">menu</i></span>
            <a href="./" class="mdui-typo-headline"><?=SITE_NAME?></a>
            <button style="position: absolute; right: 50px; border-radius: 100%" class="mdui-btn mdui-btn-icon mdui-ripple mdui-ripple-purple" mdui-tooltip="{content: '查看二维码', position: 'bottom'}" mdui-dialog="{target: '#pastebin-qr'}"><i class="mdui-icon material-icons">filter_center_focus</i></button>
            <a href="./" target="_blank" style="position: absolute; right: 5px; border-radius: 100%" class="mdui-btn mdui-btn-icon mdui-ripple mdui-ripple-purple" mdui-tooltip="{content: '新建Pastebin', position: 'bottom'}"><i class="mdui-icon material-icons">add</i></a>
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
            <a href="./fid.php?action=cookie&uri=cGFnZXMvcGFzdGViaW5QbGFpbkVkaXRvci5odG1sLnBocA==" class="mdui-list-item mdui-ripple">默认编辑器</a>
            <a href="./" class="mdui-list-item mdui-ripple mdui-list-item-active">Markdown编辑器</a>
          </div>
        </div>
            <div class="mdui-collapse-item ">
          <div class="mdui-collapse-item-header mdui-list-item mdui-ripple">
            <i class="mdui-list-item-icon mdui-icon material-icons mdui-text-color-deep-orange">account_circle</i>
            <div class="mdui-list-item-content">我的</div>
            <i class="mdui-collapse-item-arrow mdui-icon material-icons">keyboard_arrow_down</i>
          </div>
          <div class="mdui-collapse-item-body mdui-list">
                                    <a href="./fid.php?action=redirect&uri=pages/my-pb.php" class="mdui-list-item mdui-ripple ">我的Pastebin</a>
                                    <a href="./fid.php?action=redirect&uri=pages/share.php" class="mdui-list-item mdui-ripple ">我的分享</a>
                                    <a href="./fid.php?action=accountInfo" class="mdui-list-item mdui-ripple ">账号管理</a>
                                </div>
        </div>
            <div class="mdui-collapse-item ">
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
            <div class="mdui-dialog-content"><div class="center"><img src="<?=$pastebinQR?>"></div>
            <textarea id="pastebin-qr" style="display:none;"><?=$pastebinQRRawURL?></textarea>
            </div>
            <div class="mdui-dialog-actions mdui-dialog-actions-stacked">
                <button class="mdui-btn mdui-ripple" onclick="copyqr()" mdui-dialog-confirm>复制链接至剪贴板</button>
                <button class="mdui-btn mdui-ripple" mdui-dialog-close>取消</button>
            </div>
        </div>

        <div class="mdui-textfield mdui-textfield-floating-label mdui-textfield-not-empty">
            <div class="mdui-card" style="margin-top: 15px;border-radius:10px">
        <div class="mdui-card-primary mdui-typo">
            <?=$pastebinCardMessage?>
            </div></div>
            </br>
            <form action="#" method="post">
              <label class="mdui-textfield-label">标题</label>
              <input id="title" name="title" class="mdui-textfield-input" type="text" value="<?=$pastebinTitle?>" autocomplete="off" autofocus="" required=""></br>
              <div id="pastebin-editormd"><textarea name="pastebin" id="pastebin" style="display:none;"></textarea></div>
                <p><input style="float: right;" class="mdui-btn mdui-color-theme-accent mdui-ripple" type="submit" value="PASTE"></p>
            </form>
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
    <script src="https://cdn.bootcss.com/jquery/3.4.1/jquery.min.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/editormd.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/prettify.min.js"></script>
    <script type="text/javascript">
        $(function() {
            var editor = editormd("pastebin-editormd", {
                width: "100%",
                height: 540,
                markdown: "",
                emoji: true,
                path: 'https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/',
                imageUpload: false,
                toolbarIcons : function() {
                    return ["bold", "italic", "quote", "|", "h1", "h2", "h3", "h4", "|", "list-ul", "list-ol", "hr", "|", "link", "image", "code", "code-block", "table", "|", "search", "||", "watch", "preview"]
                    },
                });
            });
    </script>
    <SCRIPT LANGUAGE="JavaScript"> 
    function copyqr() 
    { 
    var input=document.getElementById("pastebin-qr");
    input.select();
    document.execCommand("Copy");
    } 
    </SCRIPT>
    <script><?=$pastebinConsoleCopy?></script>
</body>
</html>