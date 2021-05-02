<?php
	header("Content-type:text/html;charset=utf-8;");
    require_once("config/pastebinConfig.php");
    require_once("pages/pastebinFunctions.php");
    require_once("pages/fidFunctions.php");
    $pastebinEncodedRequest = (isset($_REQUEST['pb']) && strlen(base64_decode($_REQUEST['pb'])) >= 19 && strlen(base64_decode($_REQUEST['pb'])) <= 21)?base64_decode($_REQUEST['pb']):"0";
    if ($pastebinEncodedRequest)
    {
    $pastebinFileName = pastebinGetSubString($pastebinEncodedRequest, "$", "+");
	$pastebinCryptPassword = dechex(crc32(pastebinGetSubString($pastebinEncodedRequest, "+", "-")));
    $pastebinViewerType = $_REQUEST['viewerType'] ?? pastebinGetSubString($pastebinEncodedRequest, "-", "!");
    $pastebinRawAccessToken = "0";  // coming soon...
    } else{
        header('HTTP/1.0 403 Forbidden');
        exit();
    }
    $SvrName = pastebinCustomURL().str_replace('/view.php','',$_SERVER['PHP_SELF']);
    $pastebinInfo = pastebinView($pastebinFileName, $pastebinCryptPassword, "info");
    $pastebinMarkdownCardMessage = '<span><a href="'.$pastebinTLSEncryption.$SvrName.'/'.base64_encode($pastebinEncodedRequest).'&viewerType=1"><abbr title="使用默认预览查看">查看源代码</abbr></a> | <a href="'.$pastebinTLSEncryption.$SvrName.'/raw.php?id='.$pastebinFileName.'&key='.$pastebinCryptPassword.'&token='.$pastebinRawAccessToken.'" target="_blank">原始内容</a></span>';
    $pastebinCardMessage = '<span><a href="'.$pastebinTLSEncryption.$SvrName.'/raw.php?id='.$pastebinFileName.'&key='.$pastebinCryptPassword.'&token='.$pastebinRawAccessToken.'" target="_blank">原始内容</a></span>';
    $pastebinTitle = pastebinView($pastebinFileName, $pastebinCryptPassword, "title");
    $pastebin = pastebinView($pastebinFileName, $pastebinCryptPassword, "pastebin");
    $pastebinQR = pastebinQRUri($pastebinTLSEncryption.$SvrName.'/'.base64_encode($pastebinEncodedRequest), '1');
    $pastebinQRRawURL = pastebinQRUri($pastebinTLSEncryption.$SvrName.'/'.base64_encode($pastebinEncodedRequest), '0');
    if ($pastebinViewerType == "1")
    {
        require_once("pages/pastebinPlainViewer.html.php");
        exit();
    } elseif ($pastebinViewerType == "2")
    {
        require_once("pages/pastebinMarkdownViewer.html.php");
        exit();
    } else {
        header('HTTP/1.0 403 Forbidden');
        exit();
    }
