<?php
	header("Content-type:text/html;charset=utf-8;");
    require_once("config/pastebinConfig.php");
    require_once("pages/pastebinFunctions.php");
	$randomPastebinTitle = "未命名的Pastebin - ID:".randomString8("title");
    $pastebin=isset($_REQUEST['pastebin'])?$_REQUEST['pastebin']:0;
    $title=isset($_REQUEST['title'])?$_REQUEST['title']:0;
    $fidCookieCallbackURI = isset($_COOKIE['uri'])?base64_decode($_COOKIE['uri']):"pages/pastebinPlainEditor.html.php";
    $fidCookieToken = isset($_COOKIE['token'])?base64_decode($_COOKIE['token']):"0";

	if (!$pastebin || !$title) {
            $pastebinCardMessage = '请在下方进行编辑。(标题不超过'.TITLE_MAX_LENTH.'字，内容不大于'. PASTEBIN_MAX_LENTH/1024 .'KB)';
        } else {
            if (strlen($pastebin) < PASTEBIN_MAX_LENTH && strlen($title) < TITLE_MAX_LENTH){
                if ($fidCookieCallbackURI == "pages/pastebinPlainEditor.html.php") {$type = "1";} elseif ($fidCookieCallbackURI == "pages/pastebinMarkdownEditor.html.php") {$type = "2";}
                $SvrName = $_SERVER['HTTP_HOST'].str_replace('/index.php','',$_SERVER['PHP_SELF']);
                $pastebinURL = pastebinWrite($pastebin, $title, $type);
                $pastebinCardMessage = '创建成功! 链接: <span><code><a href="'.$pastebinTLSEncryption.$SvrName.'/'.$pastebinURL.'" target="_blank"><abbr title="打开链接">'.$pastebinTLSEncryption.$SvrName.'/'.$pastebinURL.'</abbr></a></code>  |  <a href="https://www.zhihu.com/qrcode?url='.$pastebinTLSEncryption.$SvrName.'/'.$pastebinURL.'" target="_blank">二维码</a></span>';
            } else {
            $pastebinCardMessage = '标题过长(不超过100字)或内容过大(不大于100KB)[PB_ERR_TOO_BIG]';
            }
        }
    require_once($fidCookieCallbackURI);
?>