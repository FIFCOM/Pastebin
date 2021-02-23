<?php
	header("Content-type:text/txt;charset=utf-8;");
    require_once("config/pastebinConfig.php");
    require_once("pages/pastebinFunctions.php");
    require_once("pages/fidFunctions.php");
    $pastebinFileName = isset($_REQUEST['id'])?$_REQUEST['id']:"0";
    $pastebinCryptPassword = isset($_REQUEST['key'])?$_REQUEST['key']:"0";
    $pastebinRawAccessToken = isset($_REQUEST['token'])?$_REQUEST['token']:"0";
    $pastebinType = isset($_REQUEST['type'])?$_REQUEST['type']:"pastebin";

    if ($pastebinFileName && $pastebinCryptPassword)
    {
        $pastebinRaw = pastebinView($pastebinFileName, $pastebinCryptPassword, $pastebinType);
        echo $pastebinRaw;
    } else{
        header('HTTP/1.0 403 Forbidden');
        exit();
    }
?>