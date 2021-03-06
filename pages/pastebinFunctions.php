<?php
if( !defined('PASTEBIN_VERSION' ) ) {
    header('HTTP/1.0 403 Forbidden');
    exit();
}

function randomString8($salt)
{
    $time = uniqid();
    return dechex(crc32("$time-$salt"));
}

function pastebinEncrypt($data, $password){
    $encrypted =  openssl_encrypt($data,'aes-128-cbc', $password, OPENSSL_RAW_DATA, PASTEBIN_CRYPT_IV);
    return $encrypted;
}

function pastebinDecrypt($data, $password){
    $decrypted =  openssl_decrypt($data,'aes-128-cbc', $password, OPENSSL_RAW_DATA, PASTEBIN_CRYPT_IV);
    return $decrypted;
}

function pastebinGetSubString($string, $start, $end) {
    $substr = substr($string, strlen($start)+strpos($string, $start),
    (strlen($string) - strpos($string, $end))*(-1));
    return $substr;
}

function pastebinTitle() {
    $pastebinAuthor = fidIsset(isset($_COOKIE['token'])?$_COOKIE['token']:0)?fidQuery($_COOKIE['token'], "token2user"):fidHideIP($_SERVER['REMOTE_ADDR']);
    $pastebinTimestamp = '20'.date("y/m/d H:i");
    return '未命名的Pastebin - ID : '.randomString8(PASTEBIN_SECURITY_TOKEN."TitleID");
}

function pastebinWrite($pastebin, $title, $viewer){
    $pastebinCryptPassword = randomString8(PASTEBIN_SECURITY_TOKEN."Crypt");
    $pastebinFileName = randomString8(PASTEBIN_SECURITY_TOKEN."FN");
    $pastebinRealCryptPassword = hash("sha256", dechex(crc32(dechex(crc32("$pastebinCryptPassword")))));
    $pastebinRealFileName = hash("sha256", "$pastebinFileName");
    $encryptedTitle = base64_encode(pastebinEncrypt($title, $pastebinRealCryptPassword));
    $encryptedPastebin = base64_encode(pastebinEncrypt($pastebin, $pastebinRealCryptPassword));
    $pastebinAuthor = fidIsset(isset($_COOKIE['token'])?$_COOKIE['token']:0)?fidQuery($_COOKIE['token'], "token2user"):fidHideIP($_SERVER['REMOTE_ADDR']);
    $encryptedInfo = base64_encode(pastebinEncrypt('Paste from '.$pastebinAuthor.' at '.'20'.date("y/m/d H:i"), $pastebinRealCryptPassword));
    $titleFP = fopen("data/title/$pastebinRealFileName.pb", 'w');
    fwrite($titleFP, $encryptedTitle . "\n");
    fclose($titleFP);
    $pastebinFP = fopen("data/pastebin/$pastebinRealFileName.pb", 'w');
    fwrite($pastebinFP, $encryptedPastebin . "\n");
    fclose($pastebinFP);
    $infoFP = fopen("data/info/$pastebinRealFileName.pb", 'w');
    fwrite($infoFP, $encryptedInfo . "\n");
    fclose($infoFP);
    return base64_encode("$"."$pastebinFileName"."+".dechex(crc32("$pastebinCryptPassword"))."-".$viewer."!");
    // $00000000+00000000-0!
}

function pastebinView($fileName, $cryptPassword, $type){
    $dataRealCryptPassword = hash("sha256", "$cryptPassword");
    $dataRealFileName = hash("sha256", "$fileName");
    if(file_exists("data/$type/$dataRealFileName.pb"))
    {
        $dataFP = fopen("data/$type/$dataRealFileName.pb", "r");
        $encryptedData = fread($dataFP, filesize("data/$type/$dataRealFileName.pb"));
        fclose($dataFP);
        $decryptedData = pastebinDecrypt(base64_decode($encryptedData), $dataRealCryptPassword);
        return $decryptedData?$decryptedData:"Pastebin.".$type.".key错误，这可能是因为链接无效/被修改/不完整。[PB_ERR_INVALID_KEY]";
    }else{
        return "Pastebin.".$type."无效或已被删除。[PB_ERR_NOT_FOUND]";
    }
}

function pastebinQRUri($string, $bool){
    return $bool?'https://www.zhihu.com/qrcode?url='.urlencode($string):$string;
}

$pastebinConsoleCopy = 'console.log(\'%cFIFCOM Pastebin  %c  '.PASTEBIN_VERSION.'%cGNU LGPL v2.1\', \'color: #fff; background: #0D47A1; font-size: 15px;border-radius:5px 0 0 5px;padding:10px 0 10px 20px;\',\'color: #fff; background: #42A5F5; font-size: 15px;border-radius:0;padding:10px 15px 10px 0px;\',\'color: #fff; background: #00695C; font-size: 15px;border-radius:0 5px 5px 0;padding:10px 20px 10px 15px;\');console.log(\'%chttps://github.com/FIFCOM/Pastebin\', \'font-size: 12px;border-radius:5px;padding:3px 10px 3px 10px;border:1px solid #00695C;\');';
$pastebinIcon = ICON_URL?ICON_URL:"https://q.qlogo.cn/headimg_dl?dst_uin=1280874899&spec=640";
$pastebinTLSEncryption = TLS_ENCRYPT == "enable"?"https://":"http://";
$pastebinPrimaryTheme = isset($_REQUEST['pastebinPrimaryTheme'])?$_REQUEST['pastebinPrimaryTheme']:PRIMARY_THEME;
$pastebinAccentTheme = isset($_REQUEST['pastebinAccentTheme'])?$_REQUEST['pastebinAccentTheme']:ACCENT_THEME;