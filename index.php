<?php
	header("Content-type:text/html;charset=utf-8;");
    require_once("config/pastebinConfig.php");
    require_once("pages/pastebinFunctions.php");
    require_once("pages/fidFunctions.php");
    setcookie("token", "1", time()+3600);
    $SvrName = $_SERVER['HTTP_HOST'].str_replace('/index.php','',$_SERVER['PHP_SELF']);
	$pastebinTitle = pastebinTitle();
    $pastebin=isset($_REQUEST['pastebin'])?$_REQUEST['pastebin']:0;
    $title=isset($_REQUEST['title'])?$_REQUEST['title']:0;
    $fidCookieCallbackURI = isset($_COOKIE['uri'])?base64_decode($_COOKIE['uri']):"pages/pastebinPlainEditor.html.php";
    $fidCookieToken = isset($_COOKIE['token'])?base64_decode($_COOKIE['token']):"0";
    $pastebinQR = pastebinQRUri($pastebinTLSEncryption.$SvrName, '1');
    $pastebinQRRawURL = pastebinQRUri($pastebinTLSEncryption.$SvrName, '0');
	if (!$pastebin || !$title) {
            $pastebinCardMessage = '请在下方进行编辑。(标题不超过'.TITLE_MAX_LENTH.'字，内容不大于'. PASTEBIN_MAX_LENTH/1024 .'KB)';
            
        } else {
            if (strlen($pastebin) < PASTEBIN_MAX_LENTH && strlen($title) < TITLE_MAX_LENTH){
                if ($fidCookieCallbackURI == "pages/pastebinPlainEditor.html.php") {$type = "1";} elseif ($fidCookieCallbackURI == "pages/pastebinMarkdownEditor.html.php") {$type = "2";}
                $pastebinURL = pastebinWrite($pastebin, $title, $type);
                $pastebinQR = pastebinQRUri($pastebinTLSEncryption.$SvrName.'/'.$pastebinURL, '1');
                $pastebinQRRawURL = pastebinQRUri($pastebinTLSEncryption.$SvrName.'/'.$pastebinURL, '0');
                $pastebinCardMessage = '创建成功! 链接: <span><code><a href="'.$pastebinTLSEncryption.$SvrName.'/'.$pastebinURL.'" target="_blank"><abbr title="打开链接">'.$pastebinTLSEncryption.$SvrName.'/'.$pastebinURL.'</abbr></a></code></span>';
            } else {
            $pastebinCardMessage = '标题过长(不超过100字)或内容过大(不大于100KB)[PB_ERR_TOO_BIG]';
            }
        }
    require_once($fidCookieCallbackURI);
?>