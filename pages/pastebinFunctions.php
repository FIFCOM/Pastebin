<?php
if (!defined('PASTEBIN_VERSION')) {
    header('HTTP/1.0 403 Forbidden');
    exit();
}

function randomToken($strLength): string
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

function encrypt($data, $password)
{
    return openssl_encrypt($data, 'aes-128-cbc', $password, OPENSSL_RAW_DATA, PASTEBIN_SECURITY_TOKEN);
}

function decrypt($data, $password)
{
    return openssl_decrypt($data, 'aes-128-cbc', $password, OPENSSL_RAW_DATA, PASTEBIN_SECURITY_TOKEN);
}

function getSubString($string, $start, $end)
{
    return substr($string, strlen($start) + strpos($string, $start),
        (strlen($string) - strpos($string, $end)) * (-1));
}

function pastebinTitle(): string
{
    return '未命名的Pastebin-ID.' . randomToken(8);
}

function write($pastebin, $title, $viewer, $expire): string
{
    $pastebinCryptPassword = randomToken(8);
    $pastebinFileName = randomToken(8);
    $pastebinRealCryptPassword = hash("sha256", dechex(crc32(dechex(crc32("$pastebinCryptPassword")))));
    $pastebinRealFileName = hash("sha256", "$pastebinFileName");
    $encryptedTitle = base64_encode(encrypt($title, $pastebinRealCryptPassword));
    $encryptedPastebin = base64_encode(encrypt($pastebin, $pastebinRealCryptPassword));
    $pastebinAuthor = hideIP($_SERVER['REMOTE_ADDR']);
    $encryptedInfo = base64_encode(encrypt('Paste from ' . $pastebinAuthor . ' at ' . '20' . date("y/m/d H:i"), $pastebinRealCryptPassword));
    $expire = $expire + date("y") * 366 + date("m") * 31 + date("d");
    $conn = mysqli_connect(PASTEBIN_DB_HOSTNAME, PASTEBIN_DB_USERNAME, PASTEBIN_DB_PASSWORD, PASTEBIN_DB_NAME);
    if (mysqli_connect_errno()) echo "FIFCOM Pastebin MySQL Connect Error : " . mysqli_connect_error();
    $sql = "INSERT INTO pastebin (filename, expire) VALUES ('$pastebinRealFileName', '$expire')";
    if ($conn->query($sql) === TRUE) {
        mysqli_close($conn);
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

function view($fileName, $cryptPassword, $type)
{
    $dataRealCryptPassword = hash("sha256", "$cryptPassword");
    $dataRealFileName = hash("sha256", "$fileName");
    if (file_exists("data/$type/$dataRealFileName.pb")) {
        $dataFP = fopen("data/$type/$dataRealFileName.pb", "r");
        $encryptedData = fread($dataFP, filesize("data/$type/$dataRealFileName.pb"));
        fclose($dataFP);
        $decryptedData = decrypt(base64_decode($encryptedData), $dataRealCryptPassword);
        return $decryptedData ?: 0;
    } else {
        return 0;
    }
}

function validateRawAccessToken($token, $id, $key): int
{
    $tmp = md5(date("y") . date("m") . date("d") . $id . $key . $_SERVER['REMOTE_ADDR'] . PASTEBIN_SECURITY_TOKEN);
    return $tmp == $token ? 1 : 0;
}

function QRUri($string, $encode): string
{
    return $encode ? 'https://www.zhihu.com/qrcode?url=' . urlencode($string) : 'https://www.zhihu.com/qrcode?url=' . $string;
}

function setUUID(): string
{
    $pastebinUUID = md5(randomToken(16));
    setcookie("uuid", $pastebinUUID, time() + 3600);
    return $pastebinUUID;
}

function connectQueryCache($uuid): string
{
    $conn = mysqli_connect(PASTEBIN_DB_HOSTNAME, PASTEBIN_DB_USERNAME, PASTEBIN_DB_PASSWORD, PASTEBIN_DB_NAME);
    if (mysqli_connect_errno()) echo "FIFCOM Pastebin MySQL Connect Error : " . mysqli_connect_error();
    $time = time() - 10000;
    $result = mysqli_query($conn, "SELECT * FROM connect_cache WHERE target = '$uuid' AND time > '$time'");
    $row = mysqli_fetch_array($result);
    if ($row) {
        $user = $row['from'];
        mysqli_query($conn, "DELETE FROM `connect_cache` WHERE `target`='$uuid' AND `from`='$user'");
        return $user;
    }
    return '';
}

function connectNew($uuid, $target): int
{
    $conn = mysqli_connect(PASTEBIN_DB_HOSTNAME, PASTEBIN_DB_USERNAME, PASTEBIN_DB_PASSWORD, PASTEBIN_DB_NAME);
    if (mysqli_connect_errno()) echo "FIFCOM Pastebin MySQL Connect Error : " . mysqli_connect_error();
    $time = time();
    $result = mysqli_query($conn, "SELECT * FROM `connect_cache` WHERE `from`='$uuid' AND `target`='$target'");
    if (mysqli_fetch_array($result) == '') {
        mysqli_query($conn, "INSERT INTO `connect_cache` (`target`, `from`, `time`) VALUES ('$target', '$uuid', '$time')");
        mysqli_close($conn);
        return 1;
    } else {
        mysqli_query($conn, "UPDATE `connect_cache` SET `time`='$time' WHERE `from`='$uuid' AND `target`='$target'");
        mysqli_close($conn);
        return 0;
    }
}

function connectWrite($uuid, $target, $url): int
{
    $conn = mysqli_connect(PASTEBIN_DB_HOSTNAME, PASTEBIN_DB_USERNAME, PASTEBIN_DB_PASSWORD, PASTEBIN_DB_NAME);
    if (mysqli_connect_errno()) echo "FIFCOM Pastebin MySQL Connect Error : " . mysqli_connect_error();
    $result = mysqli_query($conn, "SELECT * FROM `connect_url_list` WHERE `url`='$url'");
    $time = time();
    if (mysqli_fetch_array($result) == '') {
        mysqli_query($conn, "INSERT INTO `connect_url_list` (`url`, `target`, `from`, `time`, `displayed`) VALUES ('$url', '$target', '$uuid', '$time', '0')");
        mysqli_close($conn);
        return 1;
    } else {
        mysqli_close($conn);
        return 0;
    }
}

function connectQueryList($uuid, $col)
{
    $conn = mysqli_connect(PASTEBIN_DB_HOSTNAME, PASTEBIN_DB_USERNAME, PASTEBIN_DB_PASSWORD, PASTEBIN_DB_NAME);
    if (mysqli_connect_errno()) echo "FIFCOM Pastebin MySQL Connect Error : " . mysqli_connect_error();
    $time = time() - 10000;
    if ($col == 'displayed') {
        $result = mysqli_query($conn, "SELECT * FROM connect_url_list WHERE target = '$uuid' AND time > '$time'");
    } else {
        $result = mysqli_query($conn, "SELECT * FROM connect_url_list WHERE target = '$uuid' AND displayed = '0' AND time > '$time'");
    }
    while ($row = mysqli_fetch_array($result)) {
        if (!$row) return 0;
        if ($col == 'from') return $row['from'];
        if ($col == 'url') return $row['url'];
    }
}

function customURL()
{
    $url = SITE_URL ?: 0;
    return $url ?: $_SERVER['HTTP_HOST'];
}

function rawJson($pb)
{
    $id = getSubString(base64_decode($pb), "$", "+");
    $key = dechex(crc32(getSubString(base64_decode($pb), "+", "-")));
    if (view($id, $key, 'title')) {
        $json['code'] = "1";
        $json['id'] = "$id";
        $json['title'] = view($id, $key, 'title') ?: "null";
        $json['content'] = view($id, $key, 'pastebin') ?: "null";
    } else {
        $json['code'] = "0";
        $json['id'] = "$id";
        $json['title'] = "null";
        $json['content'] = "null";
    }
    header("Content-type:text/plain;charset=utf-8;");
    echo json_encode($json, JSON_UNESCAPED_UNICODE);
}

function checkTargetUUIDAlive($uuid): int
{
    $conn = mysqli_connect(PASTEBIN_DB_HOSTNAME, PASTEBIN_DB_USERNAME, PASTEBIN_DB_PASSWORD, PASTEBIN_DB_NAME);
    if (mysqli_connect_errno()) echo "FIFCOM Pastebin MySQL Connect Error : " . mysqli_connect_error();
    $time = time() - 10;
    $result = mysqli_query($conn, "SELECT uuid FROM uuid_cache WHERE uuid = '$uuid' AND time > '$time'");
    mysqli_close($conn);
    return mysqli_fetch_array($result) == '' ? 0 : 1;
    // no bug
}

function updateUUIDAlive($uuid): int
{
    //uuid_cache : uuid time
    $conn = mysqli_connect(PASTEBIN_DB_HOSTNAME, PASTEBIN_DB_USERNAME, PASTEBIN_DB_PASSWORD, PASTEBIN_DB_NAME);
    if (mysqli_connect_errno()) echo "FIFCOM Pastebin MySQL Connect Error : " . mysqli_connect_error();
    $time = time();
    $result = mysqli_query($conn, "SELECT uuid FROM uuid_cache WHERE uuid = '$uuid'");
    if (mysqli_fetch_array($result) == '') {
        mysqli_query($conn, "INSERT INTO uuid_cache (uuid, time) VALUES ('$uuid', '$time')");
    } else {
        mysqli_query($conn, "UPDATE uuid_cache SET time='$time' WHERE uuid='$uuid'");
    }
    mysqli_close($conn);
    return 1;
}

function hideIP($ip)
{
    return preg_replace('/((?:\d+\.){2})\d+/', "\\1*", $ip);
}

$consoleCopyright = 'console.log(\'%cFIFCOM Pastebin  %c  ' . PASTEBIN_VERSION . '%cGNU LGPL v2.1\', \'color: #fff; background: #0D47A1; font-size: 15px;border-radius:5px 0 0 5px;padding:10px 0 10px 20px;\',\'color: #fff; background: #42A5F5; font-size: 15px;border-radius:0;padding:10px 15px 10px 0px;\',\'color: #fff; background: #00695C; font-size: 15px;border-radius:0 5px 5px 0;padding:10px 20px 10px 15px;\');console.log(\'%c https://github.com/FIFCOM/Pastebin\', \'font-size: 12px;border-radius:5px;padding:3px 10px 3px 10px;border:1px solid #00695C;\');';
$pastebinIcon = ICON_URL ?: "https://fifcom.cn/avatar/?transparent=1";
if (TLS_ENCRYPT == 'auto' || TLS_ENCRYPT == '') {
    $scheme = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] == 'on' || (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] == 'https')) ? 'https://' : 'http://';
} else if (TLS_ENCRYPT == 'disable') $scheme = 'http://'; else if (TLS_ENCRYPT == 'enable') $scheme = 'https://';
$pastebinPrimaryTheme = $_REQUEST['pastebinPrimaryTheme'] ?? PRIMARY_THEME;
$pastebinAccentTheme = $_REQUEST['pastebinAccentTheme'] ?? ACCENT_THEME;