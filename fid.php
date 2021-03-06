<?php
	header("Content-type:text/html;charset=utf-8;");
    require_once("config/pastebinConfig.php");
    require_once("pages/pastebinFunctions.php");
    $fidAction = $_REQUEST['action'] ?? "0";
    if ($fidAction == "cookie"){
        $fidCookieCallbackURI = $_REQUEST['uri'] ?? base64_encode("pages/pastebinPlainEditor.html.php");
        $fidCookieToken = "0";
        $SvrName = $_SERVER['HTTP_HOST'].str_replace('/fid.php','',$_SERVER['PHP_SELF']);
        setcookie("uri", "$fidCookieCallbackURI", time()+3600);
        setcookie("token", "$fidCookieToken", time()+3600);
        header('Location: '.$scheme.$SvrName.'/');
    } elseif (!$fidAction) {
        header('HTTP/1.0 403 Forbidden');
        exit();
    }
