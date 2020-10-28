<?php
	header("Content-type:text/html;charset=utf-8;");
    require_once("config.php");
	$pastebin=isset($_POST['pastebin'])?base64_encode($_POST['pastebin']):0;
	if (!$pastebin) {
            $msg = 'Please enter text below.';
        } else {
            if (strlen($pastebin) < 10240||strlen($pastebin) > 0){
                $SvrName = $_SERVER['HTTP_HOST'].str_replace('/index.php','',$_SERVER['PHP_SELF']);
                $pbName = RandCRC32b();
                PBWrite($pastebin, $pbName);
                $msg = 'Generated ! ---> <span><a href="https://'.$SvrName.'/'.$pbName.'" target="_blank">https://'.$SvrName.'/'.$pbName.'</a></span>';
            } else {
            $msg = 'PasteBin string is too long. (Requires less than 10KB)';
            }
        }
    require_once("html/index.html.php");

function RandCRC32b()
{
    $time = uniqid();
    return dechex(crc32("P-A-S-T-$time-E-B-I-N"));
}

function PBWrite($pastebin, $pbName) {
    $pbName = hash("sha256", $pbName);
    $file = "pastebin-data/$pbName.pb";
    $fp = fopen($file, 'w');
    $content = $pastebin;
    fwrite($fp, $content . "\n");
    fclose($fp);
}
?>

<!--
Author: FIFCOM
https://github.com/FIFCOM/pastebin
-->
