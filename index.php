<?php
	header("Content-type:text/html;charset=utf-8;");
    $sdbName = 'example'; //Please modify the Example_String to a random string of length 16
    $accessToken = 'Example_String'; //Please modify the Example_String to a random string of length 64
	$pastebin=isset($_POST['pastebin'])?base64_encode($_POST['pastebin']):0;
	if (!$pastebin) {
            $msg = 'Please enter text below.';
        } else {
            if (strlen($pastebin) < 10240||strlen($pastebin) > 0){
                $pbName = md5($pastebin);
                $SvrName = $_SERVER['HTTP_HOST'].str_replace('/index.php','',$_SERVER['PHP_SELF']);
                $mode = 'write';
                $request = file_get_contents("http://$SvrName/sdb/sdb_$sdbName.php?accessToken=$accessToken&mode=$mode&FileName=$pbName&PasteBin=$pastebin");
                $msg = 'Generated ! ---> <span><a href="https://'.$SvrName.'/'.$pbName.'" target="_blank">https://'.$SvrName.'/'.$pbName.'</a></span>';
            } else {
            $msg = 'PasteBin string is too long. (Requires less than 10KB)';
            }
        }
    require_once("html/index.html.php");
?>

<!--
Author: FIFCOM
https://github.com/FIFCOM/pastebin
-->