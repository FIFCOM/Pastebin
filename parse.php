<?php
$sdbName = 'example'; //Please modify the Example_String to a random string of length 16
$accessToken = 'Example_String'; //Please modify the Example_String to a random string of length 64
$pbName=isset($_GET['alias'])?$_GET['alias']:0;
$SvrName = $_SERVER['HTTP_HOST'].str_replace('/parse.php','',$_SERVER['PHP_SELF']);
if ($_GET['alias']==""||$_GET['alias']==null)
{
    header("Location: https://www.fifcom.cn/error.php?reason=Empty_Alias&from=PasteBin/parse.php");
}else
{
    if (strlen($pbName) == 32)
    {
        $mode = 'read';
        $pastebin = file_get_contents("http://$SvrName/sdb/sdb_$sdbName.php?accessToken=$accessToken&mode=$mode&FileName=$pbName");
        if ($_GET['raw']=="true")
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
        $pastebin = 'Invalid PasteBin';
        require_once("html/parse.html.php");
    }
}
?>
<!--
Author: FIFCOM
https://github.com/FIFCOM/pastebin
-->