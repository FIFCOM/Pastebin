<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
$SvrName = customURL() . str_replace('/api.php', '', $_SERVER['PHP_SELF']);
$action = $_REQUEST['action'] ?? 0;
$uuid = $_REQUEST['uuid'] ?? 0;
$apikey = $_REQUEST['key'] ?? 0;

// if (!checkApiPermission($uuid, $apikey)) {header('HTTP/1.0 403 Forbidden'); exit();}

if ($action === "raw" && isset($_REQUEST['pb']) && $_REQUEST['pb'] != '') {
    rawJson($_REQUEST['pb']);
    exit();
}

if ($action === 'createPastebin') {
    if (isset($_REQUEST['title']) && $_REQUEST['title'] != ''
        && isset($_REQUEST['pastebin']) && $_REQUEST['pastebin'] != ''
        && isset($_REQUEST['type']) && $_REQUEST['type'] != ''
        && isset($_REQUEST['expire']) && $_REQUEST['expire'] != '') {
        $json['code'] = '1';
        if (strlen($_REQUEST['pastebin']) <= PASTEBIN_MAX_LENGTH * 1024 && strlen($_REQUEST['title']) <= TITLE_MAX_LENGTH) {
            $url = write($_REQUEST['pastebin'], $_REQUEST['title'], $_REQUEST['type'], $_REQUEST['expire']);
            if (isset($_REQUEST['target']) && $_REQUEST['target'] != '') {connectWrite($_COOKIE['uuid'], $_REQUEST['target'], $url);}
            $json['url'] = $scheme . $SvrName . '/' . $url;
            $json['msg'] = '<div style="color:#26A69A">√ 创建成功 链接: <span><code><a href="' . $json['url'] . '" target="_blank"><abbr title="打开链接">' . $json['url'] . '</abbr></a></code></span></div>';
            // 改: 输出raw链，样式由js决定
        } else {
            $json['url'] = null;
            $json['msg'] = '<div style="color:#e82424">× 标题过长(应少于' . TITLE_MAX_LENGTH . '字)或内容过大(应小于' . PASTEBIN_MAX_LENGTH . 'KB)[PB_TOO_BIG]</div>';
            // 改: 输出错误代码，样式由js决定
        }
    } else {
        $json['code'] = '0';
        $json['url'] = null;
        $json['msg'] = null;
    }
    echo json_encode($json, JSON_UNESCAPED_UNICODE);
    exit();
}

if ($action === 'connect') {
    if ($uuid) {
        updateUUIDAlive($uuid);
        $queryCacheUser = connectQueryCache($uuid); // BUG
        $connectQueryListJson = json_decode(connectQueryList($uuid, '0'), true);
        //echo $connectQueryListJson['code'];
        if ($queryCacheUser != '')
        {
            $json['code'] = '2';
            $json['user'] = $queryCacheUser;
        } else if ($connectQueryListJson['code'] !== '-1') {
            $json['code'] = '3';
            $json['user'] = $connectQueryListJson['from'][0];
            $pb = $connectQueryListJson['url'][0];
            $id = getSubString(base64_decode($pb), "$", "+");
            $key = dechex(crc32(getSubString(base64_decode($pb), "+", "-")));
            $json['host'] = $scheme . $SvrName . '/' ;
            $json['url'] =  $pb;
            $json['title'] = view($id, $key, 'title');
        } else {
            $json['code'] = '1';
        }
    }else {
        $json['code'] = '0';
    }
    echo json_encode($json, JSON_UNESCAPED_UNICODE);
    exit();
}

if ($action === 'connectNew') {
    if (isset($_REQUEST['target']) && $_REQUEST['target'] != '' && checkTargetUUIDAlive($_REQUEST['target'])) {
        $json['code'] = connectNew($uuid, $_REQUEST['target']) + 1;   // code = 1 : update, code = 2 : new
    } else {
        $json['code'] = 0;
    }
    echo json_encode($json, JSON_UNESCAPED_UNICODE);
    exit();
}