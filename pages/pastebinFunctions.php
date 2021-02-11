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

function pastebinWrite($pastebin, $title, $viewer){
    $pastebinCryptPassword = randomString8(PASTEBIN_SECURITY_TOKEN);
    $pastebinFileName = randomString8(PASTEBIN_SECURITY_TOKEN);
    $pastebinRealCryptPassword = hash("sha256", dechex(crc32(dechex(crc32("$pastebinCryptPassword")))));
    $pastebinRealFileName = hash("sha256", "$pastebinFileName");
    $encryptedTitle = base64_encode(pastebinEncrypt($title, $pastebinRealCryptPassword));
    $encryptedPastebin = base64_encode(pastebinEncrypt($pastebin, $pastebinRealCryptPassword));
    $titleFP = fopen("data/title/$pastebinRealFileName.pb", 'w');
    fwrite($titleFP, $encryptedTitle . "\n");
    fclose($titleFP);
    $pastebinFP = fopen("data/pastebin/$pastebinRealFileName.pb", 'w');
    fwrite($pastebinFP, $encryptedPastebin . "\n");
    fclose($pastebinFP);
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
        return $decryptedData?$decryptedData:"PastebinKey错误，这可能是因为链接被修改/不完整。[PB_ERR_INVALID_KEY]";
    }else{
        return "Pastebin无效或已被删除。[PB_ERR_NOT_FOUND]";
    }
}
$pastebinConsoleCopy = 'console.log("\n %c FIFCOM Pastebin '.PASTEBIN_VERSION.' %c https://github.com/FIFCOM/Pastebin \n\n","color: #ffffff; background: #0D47A1; padding:5px 0;","background: #42A5F5; padding:5px 0;");
console.log("\n %c LICENSE : GNU LGPL v2.1 %c https://github.com/FIFCOM/Pastebin/blob/master/LICENSE \n\n","color: #ffffff; background: #00695C; padding:5px 0;","background: #4DB6AC; padding:5px 0;");';
$pastebinIcon = ICON_URL?ICON_URL:"https://q.qlogo.cn/headimg_dl?dst_uin=1280874899&spec=640";
$pastebinTLSEncryption = TLS_ENCRYPT == "enable"?"https://":"http://";
$pastebinPrimaryTheme = isset($_REQUEST['pastebinPrimaryTheme'])?$_REQUEST['pastebinPrimaryTheme']:PRIMARY_THEME;
$pastebinAccentTheme = isset($_REQUEST['pastebinAccentTheme'])?$_REQUEST['pastebinAccentTheme']:ACCENT_THEME;