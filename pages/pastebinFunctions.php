<?php
if (!defined('PASTEBIN_VERSION')) {
    header('HTTP/1.0 403 Forbidden');
    exit();
}

function pastebinRandomToken($strLength): string
{
    $str = 'qwertyuiopasdfghjklzxcvbnm';
    $str .= 'QWERTYUIOPASDFGHJKLZXCVBNM';
    $str .= '1234567890';
    $token = '';
    for ($it = 0; $it < $strLength; $it++) try {
        $token .= $str[random_int(0, strlen($str) - 1)];
    } catch (Exception $e) {
    }
    return $token;
}

function pastebinEncrypt($data, $password)
{
    return openssl_encrypt($data, 'aes-128-cbc', $password, OPENSSL_RAW_DATA, PASTEBIN_SECURITY_TOKEN);
}

function pastebinDecrypt($data, $password)
{
    return openssl_decrypt($data, 'aes-128-cbc', $password, OPENSSL_RAW_DATA, PASTEBIN_SECURITY_TOKEN);
}

function pastebinGetSubString($string, $start, $end)
{
    return substr($string, strlen($start) + strpos($string, $start),
        (strlen($string) - strpos($string, $end)) * (-1));
}

function pastebinTitle(): string
{
    return '未命名的Pastebin-ID.' . pastebinRandomToken(8);
}

function pastebinWrite($pastebin, $title, $viewer, $expire): string
{
    $pastebinCryptPassword = pastebinRandomToken(8);
    $pastebinFileName = pastebinRandomToken(8);
    $pastebinRealCryptPassword = hash("sha256", dechex(crc32(dechex(crc32("$pastebinCryptPassword")))));
    $pastebinRealFileName = hash("sha256", "$pastebinFileName");
    $encryptedTitle = base64_encode(pastebinEncrypt($title, $pastebinRealCryptPassword));
    $encryptedPastebin = base64_encode(pastebinEncrypt($pastebin, $pastebinRealCryptPassword));
    $pastebinAuthor = fidHideIP($_SERVER['REMOTE_ADDR']);
    $encryptedInfo = base64_encode(pastebinEncrypt('Paste from ' . $pastebinAuthor . ' at ' . '20' . date("y/m/d H:i"), $pastebinRealCryptPassword));
    // FN & EXP ---> SQL
    $expire = $expire + date("y") * 366 + date("m") * 31 + date("d");
    $conn = mysqli_connect(PASTEBIN_DB_HOSTNAME, PASTEBIN_DB_USERNAME, PASTEBIN_DB_PASSWORD, PASTEBIN_DB_NAME);
    if (mysqli_connect_errno()) echo "FIFCOM Pastebin MySQL Connect Error : " . mysqli_connect_error();
    $sql = "INSERT INTO pastebin (filename, expire) VALUES ('$pastebinRealFileName', '$expire')";
    if ($conn->query($sql) === TRUE) {
        mysqli_close($conn);
        // ED ---> FS
        $titleFP = fopen("data/title/$pastebinRealFileName.pb", 'w');
        fwrite($titleFP, $encryptedTitle . "\n");
        fclose($titleFP);
        $pastebinFP = fopen("data/pastebin/$pastebinRealFileName.pb", 'w');
        fwrite($pastebinFP, $encryptedPastebin . "\n");
        fclose($pastebinFP);
        $infoFP = fopen("data/info/$pastebinRealFileName.pb", 'w');
        fwrite($infoFP, $encryptedInfo . "\n");
        fclose($infoFP);
        // link format : base64_encode($00000000+00000000-0!)
        return base64_encode("$" . "$pastebinFileName" . "+" . dechex(crc32("$pastebinCryptPassword")) . "-" . $viewer . "!");
    } else {
        mysqli_close($conn);
        return 0;
    }
}

function pastebinView($fileName, $cryptPassword, $type)
{
    $dataRealCryptPassword = hash("sha256", "$cryptPassword");
    $dataRealFileName = hash("sha256", "$fileName");
    if (file_exists("data/$type/$dataRealFileName.pb")) {
        $dataFP = fopen("data/$type/$dataRealFileName.pb", "r");
        $encryptedData = fread($dataFP, filesize("data/$type/$dataRealFileName.pb"));
        fclose($dataFP);
        $decryptedData = pastebinDecrypt(base64_decode($encryptedData), $dataRealCryptPassword);
        return $decryptedData ?: 0;
    } else {
        return 0;
    }
}

function pastebinValidateRawAccessToken($token, $id, $key): int
{
    $tmp = md5(date("y") . date("m") . date("d") . $id . $key . $_SERVER['REMOTE_ADDR'] . PASTEBIN_SECURITY_TOKEN);
    return $tmp == $token ? 1 : 0;
}

function pastebinQRUri($string, $encode): string
{
    return $encode ? 'https://www.zhihu.com/qrcode?url=' . urlencode($string) : 'https://www.zhihu.com/qrcode?url=' . $string;
}

function pastebinSenderSetID(): string
{
    $pastebinSenderID = md5(pastebinRandomToken(16));
    setcookie("senderid", base64_encode($pastebinSenderID), time() + 3600);
    return $pastebinSenderID;
}

function pastebinSenderWrite($pastebinURL, $pastebinRefID)
{
    $pastebinRealFileName = hash("sha256", "$pastebinRefID");
    $senderFP = fopen("data/sender/$pastebinRealFileName.pb", 'w');
    fwrite($senderFP, $pastebinURL);
    fclose($senderFP);
    setcookie("ref", "", time() - 3600);
}

function pastebinSenderView($senderid)
{
    $dataRealFileName = hash("sha256", "$senderid");
    if (file_exists("data/sender/$dataRealFileName.pb")) {
        $senderFP = fopen("data/sender/$dataRealFileName.pb", "r");
        $pastebinSenderURL = fread($senderFP, filesize("data/sender/$dataRealFileName.pb"));
        fclose($senderFP);
        unlink("data/sender/$dataRealFileName.pb");
        return $pastebinSenderURL;
    } else {
        return "0";
    }
}

function pastebinCustomURL()
{
    $url = SITE_URL ?: 0;
    return $url ?: $_SERVER['HTTP_HOST'];
}

$pastebinConsoleCopy = 'console.log(\'%cFIFCOM Pastebin  %c  ' . PASTEBIN_VERSION . '%cGNU LGPL v2.1\', \'color: #fff; background: #0D47A1; font-size: 15px;border-radius:5px 0 0 5px;padding:10px 0 10px 20px;\',\'color: #fff; background: #42A5F5; font-size: 15px;border-radius:0;padding:10px 15px 10px 0px;\',\'color: #fff; background: #00695C; font-size: 15px;border-radius:0 5px 5px 0;padding:10px 20px 10px 15px;\');console.log(\'%chttps://github.com/FIFCOM/Pastebin\', \'font-size: 12px;border-radius:5px;padding:3px 10px 3px 10px;border:1px solid #00695C;\');';
$pastebinIcon = ICON_URL ?: "https://q.qlogo.cn/headimg_dl?dst_uin=1280874899&spec=640";
$pastebinTLSEncryption = TLS_ENCRYPT == "enable" ? "https://" : "http://";
$pastebinPrimaryTheme = $_REQUEST['pastebinPrimaryTheme'] ?? PRIMARY_THEME;
$pastebinAccentTheme = $_REQUEST['pastebinAccentTheme'] ?? ACCENT_THEME;