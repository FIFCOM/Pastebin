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
    <meta name="keywords" content="FIFCOM PasteBin"/>
    <link rel="shortcut icon" href="<?= $pastebinIcon ?>"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/css/editormd.preview.min.css"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/css/editormd.min.css"/>
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
                <a href="./fid.php?action=cookie&uri=cGFnZXMvcGFzdGViaW5QbGFpbkVkaXRvci5odG1sLnBocA=="
                   class="mdui-list-item mdui-ripple">默认编辑器</a>
                <a href="./" class="mdui-list-item mdui-ripple mdui-list-item-active">Markdown编辑器</a>
            </div>
        </div>
        <div class="mdui-collapse-item ">
            <div class="mdui-collapse-item-header mdui-list-item mdui-ripple">
                <i class="mdui-list-item-icon mdui-icon material-icons mdui-text-color-blue">code</i>
                <div class="mdui-list-item-content">API</div>
                <i class="mdui-collapse-item-arrow mdui-icon material-icons">keyboard_arrow_down</i>
            </div>
            <div class="mdui-collapse-item-body mdui-list">
                <a href="./fid.php?action=redirect&uri=api/open-api.php" class="mdui-list-item mdui-ripple ">Open
                    API</a>
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
            </div>
        </div>
    </div>
</div>

<div class="mdui-container doc-container">
    <div class="mdui-dialog" id="pastebin-qr">
        <div class="mdui-dialog-title">二维码分享</div>
        <div class="mdui-dialog-content">
            <div class="center"><img id="qr-img" src="" width="300" height="300" alt="">
                <div class="mdui-typo-body-2-opacity">扫描二维码可向此页面快速分享Pastebin，对方创建后请刷新此页面</div>
            </div>
        </div>
        <div class="mdui-dialog-actions">
            <button class="mdui-btn mdui-ripple" mdui-dialog-close>取消</button>
        </div>
    </div>

    <div class="mdui-textfield mdui-textfield-floating-label mdui-textfield-not-empty">

        <div class="mdui-card" style="margin-top: 15px;border-radius:10px">
            <div class="mdui-card-primary mdui-typo">
                <div class="mdui-typo" id="msg"></div>
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
        <div id="connect_card"></div>
        <label class="mdui-textfield-label">标题</label>
        <label for="title"></label><input id="title" name="title" class="mdui-textfield-input" type="text"
                                          value="<?= $pastebinTitle ?>" autocomplete="off" autofocus="" required=""><br>
        <div id="pastebin-editormd"><label for="pastebin"></label><textarea name="pastebin" id="pastebin"
                                                                            style="display:none;"></textarea></div>

        <button class="mdui-btn mdui-btn-raised mdui-color-theme-accent mdui-ripple" style="float: right;" type="button"
                id="paste" onclick="createPastebin(2)">PASTE
        </button>
    </div>
</div>

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
<script src="https://cdn.bootcss.com/jquery/3.4.1/jquery.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/editormd.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/prettify.min.js"></script>
<script type="text/javascript">
    $(function () {
        const editor = editormd("pastebin-editormd", {
            width: "100%",
            height: 540,
            markdown: "",
            emoji: true,
            path: 'https://cdn.jsdelivr.net/gh/FIFCOM/editor.md@master/lib/',
            imageUpload: false,
            toolbarIcons: function () {
                return ["bold", "italic", "quote", "|", "h1", "h2", "h3", "h4", "|", "list-ul", "list-ol", "hr", "|", "link", "image", "code", "code-block", "table", "|", "search", "||", "watch", "preview"]
            },
        });
    });
</script>
<SCRIPT LANGUAGE="JavaScript">
    function copyqr() {
        const input = document.getElementById("pastebin-qr");
        input.select();
        document.execCommand("Copy");
    }
</SCRIPT>
<script>
    let $ = mdui.$;

    window.onload = function () {
        let qr = document.getElementById('qr-img')
        qr.src = "https://www.zhihu.com/qrcode?url=" + encodeURI("<?=$scheme?><?=$SvrName?>/?ref=" + getCookie("uuid"))
        if (document.cookie.indexOf("connect_target_uuid=") !== -1) {
            document.getElementById('connect_card').innerHTML = '<div class="mdui-card" style="margin-top: 15px;border-radius:10px">'
                + '<div class="mdui-card-primary mdui-typo"><label class="mdui-checkbox">'
                + '<input type="checkbox" name="target" value="'
                + getCookie('connect_target_uuid') + '"/><i class="mdui-checkbox-icon"></i>'
                + '发送给' + getCookie('connect_target_uuid').substr(0,6)  + '</label></div></div><br>'
        }
        window.setInterval(pastebinConnect, 5000);
    }

    function pastebinConnect() {
        $.ajax({
            method: 'POST',
            url: '<?=$scheme?><?=$SvrName?>/api.php?action=connect&uuid=' + getCookie("uuid"),
            //data: getCookie("uuid"),
            success: function (data) {
                let json = JSON.parse(data);
                console.log(json['code'])
                if (json['code'] === '1') {

                } else if (json['code'] === '2' && json['user'] != null) {
                    //document.cookie="connect_target_uuid=" + json['user']
                    setCookie("connect_target_uuid", json['user'], 3600)
                    document.getElementById('connect_card').innerHTML = '<div class="mdui-card" style="margin-top: 15px;border-radius:10px">'
                    + '<div class="mdui-card-primary mdui-typo"><label class="mdui-checkbox">'
                    + '<input type="checkbox" name="target" value="'
                    + json['user'] + '"/><i class="mdui-checkbox-icon"></i>'
                    + '发送给' + json['user'].substr(0,6) + '</label></div></div><br>'
                    mdui.snackbar({
                        message: json['user'] + '已连接'
                    });
                } else if (json['code'] === '3' && json['user'] != null && json['url'] != null) {
                    mdui.dialog({
                        title: json['user'] + '向你发送了一个Pastebin',
                        content: "链接 : " + json['url'] + "<br> 标题 : " + json['title'],
                        buttons: [
                            {
                                text: '关闭'
                            },
                            {
                                text: '查看',
                                onClick: function () {
                                    window.open(json['url'])
                                }
                            }
                        ]
                    });
                }
            }
        })
    }

    function createPastebin(type) {
        document.getElementById('msg').innerHTML = '正在创建...'
        let data = {}
        if ($('#pastebin').val()) {
            data['pastebin'] = $('#pastebin').val()
        }
        if ($('#title').val()) {
            data['title'] = $('#title').val()
        }
        if ($("input[name='expire']:checked").val()) {
            data['expire'] = $("input[name='expire']:checked").val()
        }
        if ($("input[name='target']:checked").val()) {
            data['target'] = $("input[name='target']:checked").val()
        }
        data['type'] = type
        $.ajax({
            method: 'POST',
            url: '<?=$scheme?><?=$SvrName?>/api.php?action=createPastebin&uuid=' + getCookie("uuid"),
            data: data,
            success: function (data) {
                let json = JSON.parse(data);
                if (json['code'] === '1') {
                    document.getElementById('msg').innerHTML = json['msg']
                    $('#title').val('未命名的Pastebin-ID.' + randomToken(8))
                    $('#pastebin').val('')
                    let qr = document.getElementById('qr-img')
                    qr.src = "https://www.zhihu.com/qrcode?url=" + encodeURI(json['url'])
                    console.log("code : 1 url : " + json['url'])
                } else if (json['code'] === '0') {
                    document.getElementById('msg').innerHTML = json['msg']
                }
                mdui.mutation()
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
    function randomToken(len) {
        len = len || 16;
        let $chars = 'QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm1234567890';
        let maxPos = $chars.length;
        let pwd = '';
        for (let i = 0; i < len; i++) {
            pwd += $chars.charAt(Math.floor(Math.random() * maxPos));
        }
        return pwd;
    }
</script>
<script><?= $consoleCopyright ?></script>
</body>
</html>