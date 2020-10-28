<?php
require_once("config.php");
$pbName=isset($_GET['pb'])?$_GET['pb']:0;
$raw=isset($_GET['raw'])?$_GET['raw']:0;
$SvrName = $_SERVER['HTTP_HOST'].str_replace('/parse.php','',$_SERVER['PHP_SELF']);
if ($_GET['pb']==""||$_GET['pb']==null)
{
    header("Location: https://www.fifcom.cn/error.php?reason=Empty_PastebinName&from=PasteBin/parse.php");
}else
{
    if (strlen($pbName) == 8)
    {
        $pastebin = GetPB($pbName);
        if ($raw=="1")
        {
            $pastebin = base64_decode($pastebin);
            echo "$pastebin";
        }else
        {
            $pastebin = base64_decode($pastebin);
            require_once("html/parse.html.php");
        }
    } else
    {
        $pastebin = 'Pastebin is invalid or has been deleted.';
        require_once("html/parse.html.php");
    }
}

function GetPB($pbName)
{
    $pbName = hash("sha256", $pbName);
    $pbPath = "pastebin-data/$pbName.pb";
    if(file_exists($pbPath))
    {
        $handle = fopen($pbPath, "r");
        $pastebin = fread($handle, filesize ($pbPath));
        fclose($handle);
        return $pastebin;
    }else{
        return "UGFzdGViaW4gaXMgaW52YWxpZCBvciBoYXMgYmVlbiBkZWxldGVkLg==";
    }
}
?>

<!--
Author: FIFCOM
https://github.com/FIFCOM/pastebin
-->
